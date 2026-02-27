"""Macroeconomic model for forward-looking ECL adjustments."""

from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import date

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MacroeconomicVariable:
    """Represents a single macroeconomic variable with historical and projected values."""

    name: str
    current_value: float
    baseline_value: float
    unit: str = ""
    description: str = ""

    def get_change(self) -> float:
        """Calculate change from baseline.

        Returns:
            Absolute change from baseline
        """
        return self.current_value - self.baseline_value

    def get_relative_change(self) -> float:
        """Calculate relative change from baseline.

        Returns:
            Relative change as decimal (e.g., 0.1 = 10%)
        """
        if self.baseline_value == 0:
            return 0.0
        return (self.current_value - self.baseline_value) / abs(self.baseline_value)


class MacroeconomicModel:
    """Model for macroeconomic variables and their projections.

    Tracks GDP growth, unemployment, interest rates, credit spreads, etc.
    and applies shocks to generate scenario-specific paths.
    """

    def __init__(self, baseline_values: Optional[Dict[str, float]] = None):
        """Initialize macroeconomic model.

        Args:
            baseline_values: Baseline values for macro variables
        """
        self.baseline_values = baseline_values or {
            'gdp_growth': 2.5,
            'unemployment_rate': 4.0,
            'interest_rate': 2.5,
            'credit_spreads': 150,  # basis points
            'house_price_index': 100.0,
            'stock_market_index': 100.0,
        }

        # Current values (start at baseline)
        self.current_values = self.baseline_values.copy()

        # Variable metadata
        self.variable_info = {
            'gdp_growth': {
                'unit': '%',
                'description': 'Real GDP growth rate (annual)',
            },
            'unemployment_rate': {
                'unit': '%',
                'description': 'Unemployment rate',
            },
            'interest_rate': {
                'unit': '%',
                'description': 'Policy interest rate',
            },
            'credit_spreads': {
                'unit': 'bps',
                'description': 'Corporate credit spreads',
            },
            'house_price_index': {
                'unit': 'index',
                'description': 'House price index',
            },
            'stock_market_index': {
                'unit': 'index',
                'description': 'Stock market index',
            },
        }

        logger.info(
            "Macroeconomic model initialized",
            baseline_values=self.baseline_values
        )

    def get_variable(self, name: str) -> MacroeconomicVariable:
        """Get macroeconomic variable.

        Args:
            name: Variable name

        Returns:
            MacroeconomicVariable object
        """
        if name not in self.current_values:
            raise KeyError(f"Unknown variable: {name}")

        info = self.variable_info.get(name, {})

        return MacroeconomicVariable(
            name=name,
            current_value=self.current_values[name],
            baseline_value=self.baseline_values[name],
            unit=info.get('unit', ''),
            description=info.get('description', ''),
        )

    def set_variable(self, name: str, value: float):
        """Set macroeconomic variable value.

        Args:
            name: Variable name
            value: New value
        """
        if name not in self.current_values:
            raise KeyError(f"Unknown variable: {name}")

        self.current_values[name] = value

        logger.debug(
            "Macro variable updated",
            variable=name,
            value=value,
            baseline=self.baseline_values[name],
            change=value - self.baseline_values[name]
        )

    def apply_shock(self, shocks: Dict[str, float]):
        """Apply shocks to macroeconomic variables.

        Args:
            shocks: Dictionary of variable name to shock amount (absolute change)
        """
        for variable, shock in shocks.items():
            if variable in self.current_values:
                old_value = self.current_values[variable]
                new_value = old_value + shock
                self.current_values[variable] = new_value

                logger.info(
                    "Applied shock to macro variable",
                    variable=variable,
                    shock=shock,
                    old_value=old_value,
                    new_value=new_value
                )
            else:
                logger.warning(f"Unknown variable in shock: {variable}")

    def apply_multiplicative_shock(self, shocks: Dict[str, float]):
        """Apply multiplicative shocks to macroeconomic variables.

        Args:
            shocks: Dictionary of variable name to shock multiplier (e.g., 0.9 = 10% decline)
        """
        for variable, multiplier in shocks.items():
            if variable in self.current_values:
                old_value = self.current_values[variable]
                new_value = old_value * multiplier
                self.current_values[variable] = new_value

                logger.info(
                    "Applied multiplicative shock",
                    variable=variable,
                    multiplier=multiplier,
                    old_value=old_value,
                    new_value=new_value
                )
            else:
                logger.warning(f"Unknown variable in shock: {variable}")

    def reset_to_baseline(self):
        """Reset all variables to baseline values."""
        self.current_values = self.baseline_values.copy()
        logger.info("Reset macro model to baseline")

    def get_all_variables(self) -> List[MacroeconomicVariable]:
        """Get all macroeconomic variables.

        Returns:
            List of MacroeconomicVariable objects
        """
        return [self.get_variable(name) for name in self.current_values.keys()]

    def get_changes_from_baseline(self) -> Dict[str, float]:
        """Get changes from baseline for all variables.

        Returns:
            Dictionary of variable name to absolute change
        """
        changes = {}
        for name in self.current_values.keys():
            changes[name] = self.current_values[name] - self.baseline_values[name]
        return changes

    def get_relative_changes_from_baseline(self) -> Dict[str, float]:
        """Get relative changes from baseline for all variables.

        Returns:
            Dictionary of variable name to relative change (as decimal)
        """
        changes = {}
        for name in self.current_values.keys():
            baseline = self.baseline_values[name]
            if baseline != 0:
                changes[name] = (self.current_values[name] - baseline) / abs(baseline)
            else:
                changes[name] = 0.0
        return changes

    def get_summary(self) -> Dict:
        """Get summary of current state.

        Returns:
            Dictionary with current values, baseline, and changes
        """
        return {
            'current_values': self.current_values.copy(),
            'baseline_values': self.baseline_values.copy(),
            'absolute_changes': self.get_changes_from_baseline(),
            'relative_changes': self.get_relative_changes_from_baseline(),
        }

    def project_forward(
        self,
        months: int,
        growth_rates: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, float]]:
        """Project variables forward with given growth rates.

        Args:
            months: Number of months to project
            growth_rates: Monthly growth rates for each variable

        Returns:
            List of dictionaries with projected values for each month
        """
        if growth_rates is None:
            growth_rates = {name: 0.0 for name in self.current_values.keys()}

        projections = []
        current = self.current_values.copy()

        for month in range(months):
            # Apply growth rates
            for variable, rate in growth_rates.items():
                if variable in current:
                    current[variable] = current[variable] * (1 + rate)

            projections.append(current.copy())

        return projections

    def apply_stress_scenario(self, scenario_name: str):
        """Apply a pre-defined stress scenario.

        Args:
            scenario_name: Name of stress scenario (recession, boom, stagflation)
        """
        stress_scenarios = {
            'recession': {
                'gdp_growth': -4.0,
                'unemployment_rate': 4.0,
                'interest_rate': -1.0,
                'credit_spreads': 250,
                'house_price_index': -20.0,
                'stock_market_index': -30.0,
            },
            'boom': {
                'gdp_growth': 2.0,
                'unemployment_rate': -2.0,
                'interest_rate': 1.0,
                'credit_spreads': -50,
                'house_price_index': 10.0,
                'stock_market_index': 20.0,
            },
            'stagflation': {
                'gdp_growth': -1.0,
                'unemployment_rate': 3.0,
                'interest_rate': 2.0,
                'credit_spreads': 150,
                'house_price_index': -5.0,
                'stock_market_index': -10.0,
            },
            'financial_crisis': {
                'gdp_growth': -3.0,
                'unemployment_rate': 3.5,
                'interest_rate': -0.5,
                'credit_spreads': 400,
                'house_price_index': -25.0,
                'stock_market_index': -40.0,
            },
        }

        if scenario_name not in stress_scenarios:
            raise ValueError(f"Unknown stress scenario: {scenario_name}")

        shocks = stress_scenarios[scenario_name]
        self.apply_shock(shocks)

        logger.info(
            "Applied stress scenario",
            scenario=scenario_name,
            changes=self.get_changes_from_baseline()
        )

    def clone(self) -> 'MacroeconomicModel':
        """Create a copy of this model.

        Returns:
            New MacroeconomicModel with same state
        """
        new_model = MacroeconomicModel(self.baseline_values.copy())
        new_model.current_values = self.current_values.copy()
        return new_model
