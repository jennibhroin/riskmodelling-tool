"""Data validation for portfolio items."""

from datetime import date
from decimal import Decimal
from typing import List, Tuple, Optional

from models.portfolio_item import PortfolioItem
from models.enums import Stage
from utils.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class PortfolioValidator:
    """Validator for portfolio data quality and business rules."""

    @classmethod
    def validate_item(
        cls,
        item: PortfolioItem,
        raise_on_error: bool = True
    ) -> Tuple[bool, List[str]]:
        """Validate a single portfolio item.

        Args:
            item: Portfolio item to validate
            raise_on_error: Whether to raise exception on validation failure

        Returns:
            Tuple of (is_valid, list of error messages)

        Raises:
            ValidationError: If validation fails and raise_on_error is True
        """
        errors = []

        # Required field checks
        errors.extend(cls._validate_required_fields(item))

        # Data type and range checks
        errors.extend(cls._validate_amounts(item))
        errors.extend(cls._validate_dates(item))
        errors.extend(cls._validate_credit_metrics(item))
        errors.extend(cls._validate_performance_metrics(item))

        # Business rule checks
        errors.extend(cls._validate_business_rules(item))

        is_valid = len(errors) == 0

        if not is_valid and raise_on_error:
            error_msg = f"Validation failed for item {item.item_id}: " + "; ".join(errors)
            raise ValidationError(error_msg)

        return is_valid, errors

    @classmethod
    def validate_portfolio(
        cls,
        items: List[PortfolioItem],
        raise_on_error: bool = False
    ) -> Tuple[int, int, List[Tuple[str, List[str]]]]:
        """Validate entire portfolio.

        Args:
            items: List of portfolio items
            raise_on_error: Whether to raise exception on any validation failure

        Returns:
            Tuple of (valid_count, invalid_count, list of (item_id, errors))

        Raises:
            ValidationError: If any validation fails and raise_on_error is True
        """
        valid_count = 0
        invalid_count = 0
        all_errors = []

        for item in items:
            is_valid, errors = cls.validate_item(item, raise_on_error=False)

            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                all_errors.append((item.item_id, errors))

                if raise_on_error:
                    error_msg = f"Validation failed for item {item.item_id}: " + "; ".join(errors)
                    raise ValidationError(error_msg)

        logger.info(
            "Portfolio validation complete",
            valid=valid_count,
            invalid=invalid_count,
            total=len(items)
        )

        return valid_count, invalid_count, all_errors

    @staticmethod
    def _validate_required_fields(item: PortfolioItem) -> List[str]:
        """Validate required fields are present."""
        errors = []

        if not item.item_id:
            errors.append("item_id is required")
        if not item.borrower_id:
            errors.append("borrower_id is required")
        if not item.origination_date:
            errors.append("origination_date is required")
        if not item.maturity_date:
            errors.append("maturity_date is required")
        if item.outstanding_amount is None:
            errors.append("outstanding_amount is required")

        return errors

    @staticmethod
    def _validate_amounts(item: PortfolioItem) -> List[str]:
        """Validate amount fields."""
        errors = []

        if item.outstanding_amount < 0:
            errors.append(f"outstanding_amount must be non-negative, got {item.outstanding_amount}")

        if item.undrawn_commitment < 0:
            errors.append(f"undrawn_commitment must be non-negative, got {item.undrawn_commitment}")

        if item.collateral_value < 0:
            errors.append(f"collateral_value must be non-negative, got {item.collateral_value}")

        if item.interest_rate < 0:
            errors.append(f"interest_rate must be non-negative, got {item.interest_rate}")

        # Check for unreasonably high values
        if item.interest_rate > 100:
            errors.append(f"interest_rate seems unreasonably high: {item.interest_rate}%")

        return errors

    @staticmethod
    def _validate_dates(item: PortfolioItem) -> List[str]:
        """Validate date fields."""
        errors = []

        today = date.today()

        # Origination should be before maturity
        if item.origination_date >= item.maturity_date:
            errors.append(
                f"origination_date ({item.origination_date}) must be before "
                f"maturity_date ({item.maturity_date})"
            )

        # Origination shouldn't be too far in the future
        if item.origination_date > today:
            errors.append(f"origination_date ({item.origination_date}) is in the future")

        # Reporting date should be between origination and maturity (with some tolerance)
        if item.reporting_date < item.origination_date:
            errors.append(
                f"reporting_date ({item.reporting_date}) is before "
                f"origination_date ({item.origination_date})"
            )

        return errors

    @staticmethod
    def _validate_credit_metrics(item: PortfolioItem) -> List[str]:
        """Validate credit metrics."""
        errors = []

        # Credit score range
        if not (300 <= item.credit_score <= 850):
            errors.append(f"credit_score must be between 300 and 850, got {item.credit_score}")

        # PD ranges
        if item.origination_pd is not None:
            if not (0 <= item.origination_pd <= 1):
                errors.append(f"origination_pd must be between 0 and 1, got {item.origination_pd}")

        if item.previous_pd is not None:
            if not (0 <= item.previous_pd <= 1):
                errors.append(f"previous_pd must be between 0 and 1, got {item.previous_pd}")

        return errors

    @staticmethod
    def _validate_performance_metrics(item: PortfolioItem) -> List[str]:
        """Validate performance metrics."""
        errors = []

        if item.days_past_due < 0:
            errors.append(f"days_past_due must be non-negative, got {item.days_past_due}")

        if item.times_past_due_12m < 0:
            errors.append(f"times_past_due_12m must be non-negative, got {item.times_past_due_12m}")

        return errors

    @staticmethod
    def _validate_business_rules(item: PortfolioItem) -> List[str]:
        """Validate business rules."""
        errors = []

        # Stage consistency with days past due
        if item.days_past_due > 90 and item.current_stage != Stage.STAGE_3:
            errors.append(
                f"Item with {item.days_past_due} days past due should be in Stage 3, "
                f"but is in {item.current_stage}"
            )

        # Stage consistency with flags
        if (item.is_forborne or item.is_restructured) and item.current_stage == Stage.STAGE_1:
            errors.append(
                "Forborne or restructured items should typically be in Stage 2 or 3, "
                f"but item is in {item.current_stage}"
            )

        # Collateral type should be set if collateral value is positive
        if item.collateral_value > 0 and not item.collateral_type:
            errors.append(
                f"collateral_type should be specified when collateral_value is {item.collateral_value}"
            )

        # Warn if loan is past maturity
        if item.reporting_date > item.maturity_date:
            errors.append(
                f"Loan is past maturity: reporting_date ({item.reporting_date}) > "
                f"maturity_date ({item.maturity_date})"
            )

        return errors


def validate_and_filter_portfolio(
    items: List[PortfolioItem],
    remove_invalid: bool = False
) -> Tuple[List[PortfolioItem], List[Tuple[str, List[str]]]]:
    """Validate portfolio and optionally remove invalid items.

    Args:
        items: List of portfolio items
        remove_invalid: If True, remove invalid items; if False, raise error

    Returns:
        Tuple of (valid items, list of (item_id, errors) for invalid items)

    Raises:
        ValidationError: If invalid items found and remove_invalid is False
    """
    validator = PortfolioValidator()

    valid_items = []
    invalid_items = []

    for item in items:
        is_valid, errors = validator.validate_item(item, raise_on_error=False)

        if is_valid:
            valid_items.append(item)
        else:
            invalid_items.append((item.item_id, errors))

            if not remove_invalid:
                error_msg = f"Invalid item {item.item_id}: " + "; ".join(errors)
                raise ValidationError(error_msg)

    if invalid_items:
        logger.warning(
            "Invalid items found",
            invalid_count=len(invalid_items),
            removed=remove_invalid
        )

    return valid_items, invalid_items
