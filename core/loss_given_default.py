"""Loss Given Default (LGD) calculations."""

from decimal import Decimal
from typing import Optional

from models.portfolio_item import PortfolioItem
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class LGDCalculator:
    """Calculate Loss Given Default (LGD) for credit exposures."""

    def __init__(self, config: Optional[dict] = None):
        """Initialize LGD calculator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or get_config().get_section('lgd')

    def calculate_lgd(
        self,
        item: PortfolioItem,
        exposure: Decimal,
        apply_downturn: bool = False
    ) -> float:
        """Calculate LGD for an exposure.

        LGD = (Exposure - Collateral Recovery) / Exposure

        Args:
            item: Portfolio item
            exposure: Exposure at default
            apply_downturn: Whether to apply downturn adjustment

        Returns:
            LGD as percentage (0-1, e.g., 0.45 = 45%)
        """
        # Calculate unsecured exposure
        unsecured_exposure = self._calculate_unsecured_exposure(item, exposure)

        # Get base LGD
        if unsecured_exposure >= exposure:
            # Fully unsecured
            base_lgd = self.config.get('unsecured_base', 0.45)
        elif unsecured_exposure == 0:
            # Fully secured
            base_lgd = self.config.get('secured_base', 0.25)
        else:
            # Partially secured - blend based on unsecured portion
            unsecured_lgd = self.config.get('unsecured_base', 0.45)
            secured_lgd = self.config.get('secured_base', 0.25)
            unsecured_ratio = float(unsecured_exposure / exposure)
            base_lgd = unsecured_ratio * unsecured_lgd + (1 - unsecured_ratio) * secured_lgd

        # Apply downturn adjustment if requested
        if apply_downturn:
            base_lgd = self.apply_downturn_adjustment(base_lgd)

        # Apply bounds
        lgd = self._apply_bounds(base_lgd)

        logger.debug(
            "Calculated LGD",
            item_id=item.item_id,
            exposure=float(exposure),
            collateral=float(item.collateral_value),
            unsecured=float(unsecured_exposure),
            lgd=lgd,
            downturn=apply_downturn
        )

        return lgd

    def apply_downturn_adjustment(
        self,
        base_lgd: float,
        downturn_multiplier: Optional[float] = None
    ) -> float:
        """Apply downturn adjustment to LGD.

        Args:
            base_lgd: Base LGD
            downturn_multiplier: Optional downturn multiplier (from config if not provided)

        Returns:
            Adjusted LGD
        """
        if downturn_multiplier is None:
            downturn_multiplier = self.config.get('downturn_multiplier', 1.25)

        adjusted_lgd = base_lgd * downturn_multiplier

        logger.debug(
            "Applied downturn adjustment",
            base_lgd=base_lgd,
            multiplier=downturn_multiplier,
            adjusted_lgd=adjusted_lgd
        )

        return adjusted_lgd

    def calculate_lgd_with_cure_rate(
        self,
        item: PortfolioItem,
        exposure: Decimal,
        cure_rate: float = 0.0
    ) -> float:
        """Calculate LGD considering cure rate.

        Args:
            item: Portfolio item
            exposure: Exposure at default
            cure_rate: Probability of cure before loss (0-1)

        Returns:
            LGD adjusted for cure rate
        """
        base_lgd = self.calculate_lgd(item, exposure)

        # Adjust LGD for cure rate
        # If cure_rate = 0.1, then 10% of defaults cure before loss
        adjusted_lgd = base_lgd * (1 - cure_rate)

        return adjusted_lgd

    def _calculate_unsecured_exposure(
        self,
        item: PortfolioItem,
        exposure: Decimal
    ) -> Decimal:
        """Calculate unsecured portion of exposure.

        Args:
            item: Portfolio item
            exposure: Total exposure

        Returns:
            Unsecured exposure
        """
        if item.collateral_value == 0:
            return exposure

        # Apply collateral haircut
        haircut = self._get_collateral_haircut(item.collateral_type)
        effective_collateral = item.collateral_value * Decimal(str(1 - haircut))

        # Calculate unsecured portion
        unsecured = exposure - effective_collateral

        return max(Decimal('0'), unsecured)

    def _get_collateral_haircut(self, collateral_type: Optional[str]) -> float:
        """Get haircut for collateral type.

        Args:
            collateral_type: Type of collateral

        Returns:
            Haircut as decimal (e.g., 0.20 = 20%)
        """
        if not collateral_type:
            return 0.0

        haircuts = self.config.get('collateral_haircuts', {})
        collateral_type_lower = collateral_type.lower().replace(' ', '_')

        return haircuts.get(collateral_type_lower, 0.30)  # Default 30% haircut

    def _apply_bounds(self, lgd: float) -> float:
        """Apply floor and ceiling to LGD.

        Args:
            lgd: LGD value

        Returns:
            Bounded LGD
        """
        floor = self.config.get('floor', 0.01)
        ceiling = self.config.get('ceiling', 1.00)

        return max(floor, min(ceiling, lgd))

    def apply_scenario_adjustment(
        self,
        base_lgd: float,
        scenario_multiplier: float,
        downturn_factor: float = 1.0
    ) -> float:
        """Apply scenario-specific adjustments to LGD.

        Args:
            base_lgd: Base LGD
            scenario_multiplier: Scenario multiplier (e.g., 1.2 for pessimistic)
            downturn_factor: Additional downturn factor

        Returns:
            Adjusted LGD
        """
        adjusted_lgd = base_lgd * scenario_multiplier * downturn_factor
        adjusted_lgd = self._apply_bounds(adjusted_lgd)

        logger.debug(
            "Applied scenario adjustment to LGD",
            base_lgd=base_lgd,
            multiplier=scenario_multiplier,
            downturn_factor=downturn_factor,
            adjusted_lgd=adjusted_lgd
        )

        return adjusted_lgd
