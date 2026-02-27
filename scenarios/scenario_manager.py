"""Scenario manager for multi-scenario ECL analysis."""

from typing import Dict, List, Optional
from pathlib import Path
from decimal import Decimal

import yaml

from models.scenario_config import ScenarioConfig, MacroeconomicAdjustments
from models.calculation_results import PortfolioECLResult
from models.portfolio_item import PortfolioItem
from scenarios.macroeconomic_model import MacroeconomicModel
from scenarios.forward_looking import ForwardLookingAdjustment
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class ScenarioManager:
    """Manages multiple economic scenarios for ECL calculation.

    Coordinates scenario creation, application to portfolios,
    and probability-weighted ECL aggregation.
    """

    def __init__(self):
        """Initialize scenario manager."""
        self.scenarios: Dict[str, ScenarioConfig] = {}
        self.macro_models: Dict[str, MacroeconomicModel] = {}
        self.forward_looking = ForwardLookingAdjustment()

        # Get baseline macro values from config
        config = get_config()
        baseline_macro = config.get('macro_variables.baseline', {})
        self.baseline_macro = MacroeconomicModel(baseline_macro)

        logger.info("Scenario manager initialized")

    def add_scenario(self, scenario: ScenarioConfig):
        """Add a scenario to the manager.

        Args:
            scenario: Scenario configuration
        """
        self.scenarios[scenario.name] = scenario

        # Create macro model for this scenario
        macro_model = self.baseline_macro.clone()
        macro_model.apply_shock(scenario.macro_adjustments.to_dict())
        self.macro_models[scenario.name] = macro_model

        logger.info(
            "Scenario added",
            name=scenario.name,
            type=str(scenario.scenario_type),
            probability=scenario.probability
        )

    def remove_scenario(self, name: str) -> bool:
        """Remove a scenario.

        Args:
            name: Scenario name

        Returns:
            True if removed, False if not found
        """
        if name in self.scenarios:
            del self.scenarios[name]
            if name in self.macro_models:
                del self.macro_models[name]
            logger.info("Scenario removed", name=name)
            return True
        return False

    def get_scenario(self, name: str) -> Optional[ScenarioConfig]:
        """Get a scenario by name.

        Args:
            name: Scenario name

        Returns:
            ScenarioConfig or None if not found
        """
        return self.scenarios.get(name)

    def list_scenarios(self) -> List[ScenarioConfig]:
        """Get list of all scenarios.

        Returns:
            List of ScenarioConfig objects
        """
        return list(self.scenarios.values())

    def get_macro_model(self, scenario_name: str) -> Optional[MacroeconomicModel]:
        """Get macroeconomic model for a scenario.

        Args:
            scenario_name: Scenario name

        Returns:
            MacroeconomicModel or None if not found
        """
        return self.macro_models.get(scenario_name)

    def load_from_config(self, config_path: str):
        """Load scenarios from YAML configuration file.

        Args:
            config_path: Path to scenarios configuration YAML
        """
        from models.enums import ScenarioType

        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Scenario config not found: {config_path}")

        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        scenarios_config = config.get('scenarios', {})

        for scenario_name, scenario_data in scenarios_config.items():
            # Create macro adjustments
            macro_data = scenario_data.get('macro_adjustments', {})
            macro_adjustments = MacroeconomicAdjustments(**macro_data)

            # Convert scenario_type string to enum
            scenario_type_str = scenario_data['scenario_type']
            if isinstance(scenario_type_str, str):
                scenario_type = ScenarioType(scenario_type_str.lower())
            else:
                scenario_type = scenario_type_str

            # Create scenario config
            scenario = ScenarioConfig(
                name=scenario_data.get('name', scenario_name),
                scenario_type=scenario_type,
                probability=scenario_data.get('probability', 0.0),
                description=scenario_data.get('description', ''),
                macro_adjustments=macro_adjustments,
                pd_multiplier=scenario_data.get('pd_multiplier', 1.0),
                lgd_multiplier=scenario_data.get('lgd_multiplier', 1.0),
                ead_multiplier=scenario_data.get('ead_multiplier', 1.0),
                lgd_downturn_factor=scenario_data.get('lgd_downturn_factor', 1.0),
                cure_rate_adjustment=scenario_data.get('cure_rate_adjustment', 0.0),
                projection_horizon_months=scenario_data.get('projection_horizon_months', 60),
            )

            self.add_scenario(scenario)

        logger.info(
            "Scenarios loaded from config",
            file=config_path,
            count=len(self.scenarios)
        )

    def create_default_scenarios(self):
        """Create default base, optimistic, and pessimistic scenarios."""
        from models.enums import ScenarioType

        # Base scenario
        base = ScenarioConfig(
            name='base',
            scenario_type=ScenarioType.BASE,
            probability=0.50,
            description='Base economic scenario with moderate growth',
        )
        self.add_scenario(base)

        # Optimistic scenario
        optimistic_macro = MacroeconomicAdjustments(
            gdp_growth=1.5,
            unemployment_rate=-1.0,
            credit_spreads=-50,
        )
        optimistic = ScenarioConfig(
            name='optimistic',
            scenario_type=ScenarioType.OPTIMISTIC,
            probability=0.25,
            description='Upside scenario with strong economic growth',
            macro_adjustments=optimistic_macro,
            pd_multiplier=0.85,
            lgd_multiplier=0.90,
        )
        self.add_scenario(optimistic)

        # Pessimistic scenario
        pessimistic_macro = MacroeconomicAdjustments(
            gdp_growth=-2.0,
            unemployment_rate=2.0,
            credit_spreads=100,
        )
        pessimistic = ScenarioConfig(
            name='pessimistic',
            scenario_type=ScenarioType.PESSIMISTIC,
            probability=0.25,
            description='Downside scenario with economic contraction',
            macro_adjustments=pessimistic_macro,
            pd_multiplier=1.30,
            lgd_multiplier=1.20,
        )
        self.add_scenario(pessimistic)

        logger.info("Default scenarios created", count=3)

    def validate_probabilities(self) -> bool:
        """Validate that scenario probabilities sum to 1.0.

        Returns:
            True if valid, False otherwise
        """
        total_prob = sum(s.probability for s in self.scenarios.values())
        is_valid = abs(total_prob - 1.0) < 0.01  # Allow 1% tolerance

        if not is_valid:
            logger.warning(
                "Scenario probabilities do not sum to 1.0",
                total=total_prob,
                scenarios={name: s.probability for name, s in self.scenarios.items()}
            )

        return is_valid

    def normalize_probabilities(self):
        """Normalize scenario probabilities to sum to 1.0."""
        total_prob = sum(s.probability for s in self.scenarios.values())

        if total_prob == 0:
            # Equal weight all scenarios
            equal_prob = 1.0 / len(self.scenarios)
            for scenario in self.scenarios.values():
                scenario.probability = equal_prob
        else:
            # Normalize
            for scenario in self.scenarios.values():
                scenario.probability = scenario.probability / total_prob

        logger.info(
            "Probabilities normalized",
            probabilities={name: s.probability for name, s in self.scenarios.items()}
        )

    def calculate_weighted_ecl(
        self,
        scenario_results: Dict[str, PortfolioECLResult]
    ) -> Decimal:
        """Calculate probability-weighted ECL across scenarios.

        Args:
            scenario_results: Dictionary mapping scenario name to ECL result

        Returns:
            Probability-weighted total ECL
        """
        weighted_ecl = Decimal('0')

        for scenario_name, result in scenario_results.items():
            scenario = self.scenarios.get(scenario_name)
            if scenario:
                weight = Decimal(str(scenario.probability))
                contribution = result.total_ecl * weight
                weighted_ecl += contribution

                logger.debug(
                    "Scenario ECL contribution",
                    scenario=scenario_name,
                    ecl=float(result.total_ecl),
                    probability=scenario.probability,
                    contribution=float(contribution)
                )
            else:
                logger.warning(
                    "Scenario not found for result",
                    scenario=scenario_name
                )

        logger.info(
            "Calculated weighted ECL",
            weighted_ecl=float(weighted_ecl),
            scenario_count=len(scenario_results)
        )

        return weighted_ecl

    def calculate_weighted_portfolio_result(
        self,
        scenario_results: Dict[str, PortfolioECLResult]
    ) -> PortfolioECLResult:
        """Create a probability-weighted portfolio ECL result.

        Args:
            scenario_results: Dictionary mapping scenario name to ECL result

        Returns:
            Weighted PortfolioECLResult
        """
        if not scenario_results:
            raise ValueError("No scenario results provided")

        # Use first result as template
        first_result = next(iter(scenario_results.values()))

        # Calculate weighted values
        weighted_total_ecl = Decimal('0')
        weighted_stage_1_ecl = Decimal('0')
        weighted_stage_2_ecl = Decimal('0')
        weighted_stage_3_ecl = Decimal('0')

        for scenario_name, result in scenario_results.items():
            scenario = self.scenarios.get(scenario_name)
            if scenario:
                weight = Decimal(str(scenario.probability))
                weighted_total_ecl += result.total_ecl * weight
                weighted_stage_1_ecl += result.stage_1_ecl * weight
                weighted_stage_2_ecl += result.stage_2_ecl * weight
                weighted_stage_3_ecl += result.stage_3_ecl * weight

        # Create weighted result
        weighted_result = PortfolioECLResult(
            total_ecl=weighted_total_ecl,
            total_exposure=first_result.total_exposure,
            total_items=first_result.total_items,
            stage_1_ecl=weighted_stage_1_ecl,
            stage_2_ecl=weighted_stage_2_ecl,
            stage_3_ecl=weighted_stage_3_ecl,
            stage_1_exposure=first_result.stage_1_exposure,
            stage_2_exposure=first_result.stage_2_exposure,
            stage_3_exposure=first_result.stage_3_exposure,
            stage_1_count=first_result.stage_1_count,
            stage_2_count=first_result.stage_2_count,
            stage_3_count=first_result.stage_3_count,
            scenario_name='probability_weighted',
            calculation_date=first_result.calculation_date,
        )

        return weighted_result

    def get_scenario_comparison(
        self,
        scenario_results: Dict[str, PortfolioECLResult]
    ) -> Dict:
        """Get comparison of ECL across scenarios.

        Args:
            scenario_results: Dictionary mapping scenario name to ECL result

        Returns:
            Dictionary with comparison statistics
        """
        comparison = {
            'scenarios': {},
            'weighted_ecl': float(self.calculate_weighted_ecl(scenario_results)),
        }

        for scenario_name, result in scenario_results.items():
            scenario = self.scenarios.get(scenario_name)
            comparison['scenarios'][scenario_name] = {
                'probability': scenario.probability if scenario else 0.0,
                'total_ecl': float(result.total_ecl),
                'coverage_ratio': result.coverage_ratio,
                'stage_1_ecl': float(result.stage_1_ecl),
                'stage_2_ecl': float(result.stage_2_ecl),
                'stage_3_ecl': float(result.stage_3_ecl),
            }

        # Add min/max/range statistics
        ecl_values = [float(r.total_ecl) for r in scenario_results.values()]
        comparison['min_ecl'] = min(ecl_values)
        comparison['max_ecl'] = max(ecl_values)
        comparison['range_ecl'] = max(ecl_values) - min(ecl_values)

        return comparison

    def apply_scenario_to_portfolio(
        self,
        items: List[PortfolioItem],
        scenario_name: str
    ) -> List[PortfolioItem]:
        """Apply scenario-specific adjustments to portfolio items.

        Note: Currently scenarios are applied via ECL engine.
        This method is for future enhancements that might modify
        item attributes directly.

        Args:
            items: Portfolio items
            scenario_name: Scenario to apply

        Returns:
            Modified portfolio items (currently returns originals)
        """
        scenario = self.get_scenario(scenario_name)
        if not scenario:
            logger.warning(f"Scenario not found: {scenario_name}")
            return items

        logger.info(
            "Applying scenario to portfolio",
            scenario=scenario_name,
            item_count=len(items)
        )

        # For now, return items unchanged
        # Scenario adjustments are applied during ECL calculation
        return items

    def get_summary(self) -> Dict:
        """Get summary of all scenarios.

        Returns:
            Dictionary with scenario summaries
        """
        scenarios_summary = {}

        for name, scenario in self.scenarios.items():
            macro_model = self.macro_models.get(name)
            macro_changes = macro_model.get_changes_from_baseline() if macro_model else {}

            scenarios_summary[name] = {
                'type': str(scenario.scenario_type),
                'probability': scenario.probability,
                'description': scenario.description,
                'pd_multiplier': scenario.pd_multiplier,
                'lgd_multiplier': scenario.lgd_multiplier,
                'ead_multiplier': scenario.ead_multiplier,
                'macro_changes': macro_changes,
            }

        return {
            'scenario_count': len(self.scenarios),
            'total_probability': sum(s.probability for s in self.scenarios.values()),
            'scenarios': scenarios_summary,
        }
