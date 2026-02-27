"""ECL calculation result data models."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Dict, List

from .enums import Stage, ScenarioType


@dataclass
class ECLResult:
    """Result of ECL calculation for a single portfolio item.

    Contains all components of the ECL calculation including PD, LGD, EAD,
    and the final ECL amount.
    """
    item_id: str
    stage: Stage

    # ECL components
    probability_of_default: float  # PD
    loss_given_default: float  # LGD (as percentage)
    exposure_at_default: Decimal  # EAD

    # ECL amounts
    ecl_amount: Decimal  # Final ECL = PD × LGD × EAD

    # Time horizon
    time_horizon_months: int  # 12 for Stage 1, lifetime for Stage 2/3

    # Scenario information
    scenario_name: Optional[str] = None
    scenario_type: Optional[ScenarioType] = None

    # Breakdown by time period (for lifetime ECL)
    period_ecl: Optional[List[Decimal]] = None  # ECL by period
    period_pd: Optional[List[float]] = None  # Marginal PD by period

    # Collateral impact
    collateral_value: Decimal = Decimal('0')
    unsecured_exposure: Decimal = Decimal('0')

    # Additional metrics
    discount_rate: float = 0.0
    present_value_ecl: Optional[Decimal] = None

    def __post_init__(self):
        """Validate and convert types."""
        if not isinstance(self.ecl_amount, Decimal):
            self.ecl_amount = Decimal(str(self.ecl_amount))
        if not isinstance(self.exposure_at_default, Decimal):
            self.exposure_at_default = Decimal(str(self.exposure_at_default))
        if not isinstance(self.collateral_value, Decimal):
            self.collateral_value = Decimal(str(self.collateral_value))
        if not isinstance(self.unsecured_exposure, Decimal):
            self.unsecured_exposure = Decimal(str(self.unsecured_exposure))

        # Convert stage string to enum
        if isinstance(self.stage, str):
            self.stage = Stage(self.stage)

        # Convert scenario type string to enum
        if isinstance(self.scenario_type, str):
            self.scenario_type = ScenarioType(self.scenario_type)

    @property
    def ecl_rate(self) -> float:
        """ECL as percentage of exposure."""
        if self.exposure_at_default > 0:
            return float(self.ecl_amount / self.exposure_at_default)
        return 0.0

    @property
    def coverage_ratio(self) -> float:
        """ECL coverage ratio (ECL / Outstanding)."""
        return self.ecl_rate

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'item_id': self.item_id,
            'stage': str(self.stage),
            'probability_of_default': self.probability_of_default,
            'loss_given_default': self.loss_given_default,
            'exposure_at_default': float(self.exposure_at_default),
            'ecl_amount': float(self.ecl_amount),
            'ecl_rate': self.ecl_rate,
            'time_horizon_months': self.time_horizon_months,
            'scenario_name': self.scenario_name,
            'scenario_type': str(self.scenario_type) if self.scenario_type else None,
            'collateral_value': float(self.collateral_value),
            'unsecured_exposure': float(self.unsecured_exposure),
            'discount_rate': self.discount_rate,
            'present_value_ecl': float(self.present_value_ecl) if self.present_value_ecl else None,
        }


@dataclass
class PortfolioECLResult:
    """Aggregated ECL results for entire portfolio.

    Contains portfolio-level statistics and breakdowns by stage, sector,
    and other dimensions.
    """
    # Overall totals
    total_ecl: Decimal
    total_exposure: Decimal
    total_items: int

    # Breakdown by stage
    stage_1_ecl: Decimal = Decimal('0')
    stage_2_ecl: Decimal = Decimal('0')
    stage_3_ecl: Decimal = Decimal('0')

    stage_1_exposure: Decimal = Decimal('0')
    stage_2_exposure: Decimal = Decimal('0')
    stage_3_exposure: Decimal = Decimal('0')

    stage_1_count: int = 0
    stage_2_count: int = 0
    stage_3_count: int = 0

    # Individual item results
    item_results: List[ECLResult] = field(default_factory=list)

    # Breakdown by other dimensions
    ecl_by_sector: Dict[str, Decimal] = field(default_factory=dict)
    ecl_by_product: Dict[str, Decimal] = field(default_factory=dict)
    ecl_by_rating: Dict[str, Decimal] = field(default_factory=dict)

    # Scenario information
    scenario_name: Optional[str] = None
    scenario_type: Optional[ScenarioType] = None
    scenario_probability: Optional[float] = None

    # Calculation metadata
    calculation_date: Optional[str] = None
    calculation_method: Optional[str] = None

    def __post_init__(self):
        """Validate and convert types."""
        if not isinstance(self.total_ecl, Decimal):
            self.total_ecl = Decimal(str(self.total_ecl))
        if not isinstance(self.total_exposure, Decimal):
            self.total_exposure = Decimal(str(self.total_exposure))

        for attr in ['stage_1_ecl', 'stage_2_ecl', 'stage_3_ecl',
                     'stage_1_exposure', 'stage_2_exposure', 'stage_3_exposure']:
            value = getattr(self, attr)
            if not isinstance(value, Decimal):
                setattr(self, attr, Decimal(str(value)))

    @property
    def coverage_ratio(self) -> float:
        """Overall ECL coverage ratio."""
        if self.total_exposure > 0:
            return float(self.total_ecl / self.total_exposure)
        return 0.0

    @property
    def stage_1_coverage(self) -> float:
        """Stage 1 coverage ratio."""
        if self.stage_1_exposure > 0:
            return float(self.stage_1_ecl / self.stage_1_exposure)
        return 0.0

    @property
    def stage_2_coverage(self) -> float:
        """Stage 2 coverage ratio."""
        if self.stage_2_exposure > 0:
            return float(self.stage_2_ecl / self.stage_2_exposure)
        return 0.0

    @property
    def stage_3_coverage(self) -> float:
        """Stage 3 coverage ratio."""
        if self.stage_3_exposure > 0:
            return float(self.stage_3_ecl / self.stage_3_exposure)
        return 0.0

    @property
    def stage_2_ratio(self) -> float:
        """Stage 2 ratio (Stage 2 exposure / Total exposure)."""
        if self.total_exposure > 0:
            return float(self.stage_2_exposure / self.total_exposure)
        return 0.0

    @property
    def stage_3_ratio(self) -> float:
        """Stage 3 ratio (Stage 3 exposure / Total exposure)."""
        if self.total_exposure > 0:
            return float(self.stage_3_exposure / self.total_exposure)
        return 0.0

    def get_summary(self) -> dict:
        """Get summary statistics as dictionary."""
        return {
            'total_ecl': float(self.total_ecl),
            'total_exposure': float(self.total_exposure),
            'coverage_ratio': self.coverage_ratio,
            'total_items': self.total_items,
            'stage_1': {
                'ecl': float(self.stage_1_ecl),
                'exposure': float(self.stage_1_exposure),
                'count': self.stage_1_count,
                'coverage': self.stage_1_coverage,
            },
            'stage_2': {
                'ecl': float(self.stage_2_ecl),
                'exposure': float(self.stage_2_exposure),
                'count': self.stage_2_count,
                'coverage': self.stage_2_coverage,
                'ratio': self.stage_2_ratio,
            },
            'stage_3': {
                'ecl': float(self.stage_3_ecl),
                'exposure': float(self.stage_3_exposure),
                'count': self.stage_3_count,
                'coverage': self.stage_3_coverage,
                'ratio': self.stage_3_ratio,
            },
            'scenario_name': self.scenario_name,
            'calculation_date': self.calculation_date,
        }

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            **self.get_summary(),
            'ecl_by_sector': {k: float(v) for k, v in self.ecl_by_sector.items()},
            'ecl_by_product': {k: float(v) for k, v in self.ecl_by_product.items()},
            'ecl_by_rating': {k: float(v) for k, v in self.ecl_by_rating.items()},
        }
