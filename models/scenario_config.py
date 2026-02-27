"""Scenario configuration data models."""

from dataclasses import dataclass, field
from typing import Dict, Optional

from .enums import ScenarioType


@dataclass
class MacroeconomicAdjustments:
    """Macroeconomic variable adjustments for a scenario."""
    gdp_growth: float = 0.0  # Percentage points change
    unemployment_rate: float = 0.0  # Percentage points change
    interest_rate: float = 0.0  # Basis points change
    credit_spreads: float = 0.0  # Basis points change
    house_price_index: float = 0.0  # Percentage change
    stock_market_index: float = 0.0  # Percentage change

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'gdp_growth': self.gdp_growth,
            'unemployment_rate': self.unemployment_rate,
            'interest_rate': self.interest_rate,
            'credit_spreads': self.credit_spreads,
            'house_price_index': self.house_price_index,
            'stock_market_index': self.stock_market_index,
        }


@dataclass
class ScenarioConfig:
    """Configuration for an economic scenario.

    Defines the scenario type, probability weight, and macroeconomic
    adjustments to apply when calculating ECL under this scenario.
    """
    name: str
    scenario_type: ScenarioType
    probability: float = 1.0  # Probability weight (should sum to 1.0 across scenarios)
    description: str = ""

    # Macroeconomic adjustments
    macro_adjustments: MacroeconomicAdjustments = field(default_factory=MacroeconomicAdjustments)

    # PD/LGD adjustment factors
    pd_multiplier: float = 1.0  # Direct multiplier on PD
    lgd_multiplier: float = 1.0  # Direct multiplier on LGD
    ead_multiplier: float = 1.0  # Direct multiplier on EAD (e.g., for CCF changes)

    # Downturn factors
    lgd_downturn_factor: float = 1.0  # Additional downturn adjustment for LGD
    cure_rate_adjustment: float = 0.0  # Adjustment to cure rates

    # Forward-looking projection periods
    projection_horizon_months: int = 60  # How far to project forward

    def __post_init__(self):
        """Validate scenario configuration."""
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"Probability must be between 0 and 1, got {self.probability}")

        if self.projection_horizon_months < 1:
            raise ValueError("Projection horizon must be at least 1 month")

        # Convert string to enum if needed
        if isinstance(self.scenario_type, str):
            self.scenario_type = ScenarioType(self.scenario_type)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'name': self.name,
            'scenario_type': str(self.scenario_type),
            'probability': self.probability,
            'description': self.description,
            'macro_adjustments': self.macro_adjustments.to_dict(),
            'pd_multiplier': self.pd_multiplier,
            'lgd_multiplier': self.lgd_multiplier,
            'ead_multiplier': self.ead_multiplier,
            'lgd_downturn_factor': self.lgd_downturn_factor,
            'cure_rate_adjustment': self.cure_rate_adjustment,
            'projection_horizon_months': self.projection_horizon_months,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScenarioConfig':
        """Create ScenarioConfig from dictionary."""
        macro_data = data.pop('macro_adjustments', {})
        macro_adjustments = MacroeconomicAdjustments(**macro_data)
        return cls(macro_adjustments=macro_adjustments, **data)
