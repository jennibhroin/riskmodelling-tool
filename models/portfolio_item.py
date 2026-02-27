"""Portfolio item data model."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from decimal import Decimal

from .enums import Stage


@dataclass
class PortfolioItem:
    """Represents a single credit exposure in the portfolio.

    Contains all attributes needed for IFRS 9 ECL calculation including
    exposure details, credit metrics, and historical information.
    """

    # Identifiers
    item_id: str
    borrower_id: str

    # Dates
    origination_date: date
    maturity_date: date

    # Exposure amounts (required field)
    outstanding_amount: Decimal

    # Optional fields with defaults
    reporting_date: date = field(default_factory=date.today)
    undrawn_commitment: Decimal = Decimal('0')
    interest_rate: float = 0.0

    # Classification
    sector: str = "Other"
    product_type: str = "Term Loan"
    currency: str = "USD"

    # Collateral
    collateral_value: Decimal = Decimal('0')
    collateral_type: Optional[str] = None

    # Credit metrics
    credit_score: int = 500
    internal_rating: Optional[str] = None
    external_rating: Optional[str] = None

    # Performance
    days_past_due: int = 0
    times_past_due_12m: int = 0
    is_forborne: bool = False
    is_restructured: bool = False

    # Staging
    current_stage: Stage = Stage.STAGE_1
    previous_stage: Optional[Stage] = None
    origination_stage: Stage = Stage.STAGE_1

    # Historical PD (for SICR detection)
    origination_pd: Optional[float] = None
    previous_pd: Optional[float] = None

    # Additional attributes
    country: str = "US"
    region: Optional[str] = None

    def __post_init__(self):
        """Validate and convert types after initialization."""
        # Convert to Decimal if needed
        if not isinstance(self.outstanding_amount, Decimal):
            self.outstanding_amount = Decimal(str(self.outstanding_amount))
        if not isinstance(self.undrawn_commitment, Decimal):
            self.undrawn_commitment = Decimal(str(self.undrawn_commitment))
        if not isinstance(self.collateral_value, Decimal):
            self.collateral_value = Decimal(str(self.collateral_value))

        # Convert to date if needed
        if isinstance(self.origination_date, str):
            self.origination_date = date.fromisoformat(self.origination_date)
        if isinstance(self.maturity_date, str):
            self.maturity_date = date.fromisoformat(self.maturity_date)
        if isinstance(self.reporting_date, str):
            self.reporting_date = date.fromisoformat(self.reporting_date)

        # Convert stage strings to enum
        if isinstance(self.current_stage, str):
            self.current_stage = Stage(self.current_stage)
        if isinstance(self.previous_stage, str):
            self.previous_stage = Stage(self.previous_stage)
        if isinstance(self.origination_stage, str):
            self.origination_stage = Stage(self.origination_stage)

    @property
    def total_exposure(self) -> Decimal:
        """Total exposure at default (outstanding + undrawn)."""
        return self.outstanding_amount + self.undrawn_commitment

    @property
    def loan_to_value(self) -> float:
        """Loan-to-value ratio (outstanding / collateral)."""
        if self.collateral_value > 0:
            return float(self.outstanding_amount / self.collateral_value)
        return float('inf')

    @property
    def remaining_term_months(self) -> int:
        """Remaining term in months from reporting date to maturity."""
        if self.maturity_date <= self.reporting_date:
            return 0
        delta = self.maturity_date - self.reporting_date
        return max(0, int(delta.days / 30.44))  # Average days per month

    @property
    def age_months(self) -> int:
        """Age of loan in months from origination to reporting date."""
        delta = self.reporting_date - self.origination_date
        return int(delta.days / 30.44)

    @property
    def is_past_due(self) -> bool:
        """Check if loan has any days past due."""
        return self.days_past_due > 0

    @property
    def is_defaulted(self) -> bool:
        """Check if loan meets default criteria (>90 DPD or Stage 3)."""
        return self.days_past_due > 90 or self.current_stage == Stage.STAGE_3

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'item_id': self.item_id,
            'borrower_id': self.borrower_id,
            'origination_date': self.origination_date.isoformat(),
            'maturity_date': self.maturity_date.isoformat(),
            'reporting_date': self.reporting_date.isoformat(),
            'outstanding_amount': float(self.outstanding_amount),
            'undrawn_commitment': float(self.undrawn_commitment),
            'interest_rate': self.interest_rate,
            'sector': self.sector,
            'product_type': self.product_type,
            'currency': self.currency,
            'collateral_value': float(self.collateral_value),
            'collateral_type': self.collateral_type,
            'credit_score': self.credit_score,
            'internal_rating': self.internal_rating,
            'external_rating': self.external_rating,
            'days_past_due': self.days_past_due,
            'times_past_due_12m': self.times_past_due_12m,
            'is_forborne': self.is_forborne,
            'is_restructured': self.is_restructured,
            'current_stage': str(self.current_stage),
            'previous_stage': str(self.previous_stage) if self.previous_stage else None,
            'origination_stage': str(self.origination_stage),
            'origination_pd': self.origination_pd,
            'previous_pd': self.previous_pd,
            'country': self.country,
            'region': self.region,
        }
