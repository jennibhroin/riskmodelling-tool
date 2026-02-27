"""Integration tests for scenario workflow."""

import pytest
from datetime import date
from decimal import Decimal
from pathlib import Path

from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine
from scenarios.scenario_manager import ScenarioManager
from scenarios.macroeconomic_model import MacroeconomicModel
from scenarios.forward_looking import ForwardLookingAdjustment
from models.scenario_config import ScenarioConfig, MacroeconomicAdjustments
from models.enums import ScenarioType


class TestMacroeconomicModel:
    """Tests for MacroeconomicModel."""

    def test_model_initialization(self):
        """Test model initialization with baseline values."""
        baseline = {
            'gdp_growth': 2.5,
            'unemployment_rate': 4.0,
        }
        model = MacroeconomicModel(baseline)

        assert model.baseline_values == baseline
        assert model.current_values == baseline

    def test_apply_shock(self):
        """Test applying shocks to variables."""
        model = MacroeconomicModel()
        initial_gdp = model.current_values['gdp_growth']

        model.apply_shock({'gdp_growth': -2.0})

        assert model.current_values['gdp_growth'] == initial_gdp - 2.0

    def test_apply_multiplicative_shock(self):
        """Test applying multiplicative shocks."""
        model = MacroeconomicModel()
        initial_gdp = model.current_values['gdp_growth']

        model.apply_multiplicative_shock({'gdp_growth': 0.5})

        assert model.current_values['gdp_growth'] == initial_gdp * 0.5

    def test_get_variable(self):
        """Test getting macro variable."""
        model = MacroeconomicModel()
        var = model.get_variable('gdp_growth')

        assert var.name == 'gdp_growth'
        assert var.current_value == var.baseline_value

    def test_get_changes_from_baseline(self):
        """Test calculating changes from baseline."""
        model = MacroeconomicModel()
        model.apply_shock({'gdp_growth': -2.0})

        changes = model.get_changes_from_baseline()

        assert changes['gdp_growth'] == -2.0

    def test_reset_to_baseline(self):
        """Test resetting to baseline."""
        model = MacroeconomicModel()
        model.apply_shock({'gdp_growth': -2.0})

        model.reset_to_baseline()

        assert model.current_values == model.baseline_values

    def test_apply_stress_scenario(self):
        """Test applying pre-defined stress scenarios."""
        model = MacroeconomicModel()

        model.apply_stress_scenario('recession')

        changes = model.get_changes_from_baseline()
        assert changes['gdp_growth'] < 0
        assert changes['unemployment_rate'] > 0

    def test_clone(self):
        """Test cloning model."""
        model = MacroeconomicModel()
        model.apply_shock({'gdp_growth': -2.0})

        clone = model.clone()

        assert clone.current_values == model.current_values
        assert clone.baseline_values == model.baseline_values
        assert clone is not model


class TestForwardLookingAdjustment:
    """Tests for ForwardLookingAdjustment."""

    @pytest.fixture
    def base_macro_model(self):
        """Create base macro model."""
        return MacroeconomicModel()

    @pytest.fixture
    def stressed_macro_model(self):
        """Create stressed macro model."""
        model = MacroeconomicModel()
        model.apply_shock({
            'gdp_growth': -2.0,
            'unemployment_rate': 2.0,
            'credit_spreads': 100,
        })
        return model

    def test_adjust_pd_base_scenario(self, base_macro_model):
        """Test PD adjustment in base scenario (no change)."""
        adjuster = ForwardLookingAdjustment()
        base_pd = 0.02

        adjusted_pd = adjuster.adjust_pd(base_pd, base_macro_model)

        # Should be close to base PD (no macro changes)
        assert abs(adjusted_pd - base_pd) < 0.001

    def test_adjust_pd_stress_scenario(self, stressed_macro_model):
        """Test PD adjustment in stress scenario."""
        adjuster = ForwardLookingAdjustment()
        base_pd = 0.02

        adjusted_pd = adjuster.adjust_pd(base_pd, stressed_macro_model)

        # PD should increase in stress scenario
        assert adjusted_pd > base_pd

    def test_adjust_lgd_stress_scenario(self, stressed_macro_model):
        """Test LGD adjustment in stress scenario."""
        adjuster = ForwardLookingAdjustment()
        base_lgd = 0.45

        adjusted_lgd = adjuster.adjust_lgd(base_lgd, stressed_macro_model)

        # LGD should increase in stress scenario (unemployment up)
        assert adjusted_lgd > base_lgd

    def test_adjust_ead_stress_scenario(self, stressed_macro_model):
        """Test EAD adjustment in stress scenario."""
        adjuster = ForwardLookingAdjustment()
        base_ead = 1000000.0

        adjusted_ead = adjuster.adjust_ead(base_ead, stressed_macro_model)

        # EAD should increase in stress scenario (higher drawdowns)
        assert adjusted_ead > base_ead

    def test_calculate_scenario_multipliers(self, stressed_macro_model):
        """Test calculating scenario multipliers."""
        adjuster = ForwardLookingAdjustment()

        multipliers = adjuster.calculate_scenario_multipliers(stressed_macro_model)

        assert 'pd_multiplier' in multipliers
        assert 'lgd_multiplier' in multipliers
        assert 'ead_multiplier' in multipliers

        # All multipliers should be > 1.0 in stress scenario
        assert multipliers['pd_multiplier'] > 1.0
        assert multipliers['lgd_multiplier'] > 1.0


class TestScenarioManager:
    """Tests for ScenarioManager."""

    @pytest.fixture
    def scenario_manager(self):
        """Create scenario manager."""
        return ScenarioManager()

    @pytest.fixture
    def sample_scenario(self):
        """Create sample scenario."""
        macro_adj = MacroeconomicAdjustments(
            gdp_growth=-2.0,
            unemployment_rate=2.0,
        )
        return ScenarioConfig(
            name='test_scenario',
            scenario_type=ScenarioType.PESSIMISTIC,
            probability=0.5,
            macro_adjustments=macro_adj,
        )

    def test_add_scenario(self, scenario_manager, sample_scenario):
        """Test adding scenario."""
        scenario_manager.add_scenario(sample_scenario)

        assert 'test_scenario' in scenario_manager.scenarios
        assert scenario_manager.get_scenario('test_scenario') == sample_scenario

    def test_remove_scenario(self, scenario_manager, sample_scenario):
        """Test removing scenario."""
        scenario_manager.add_scenario(sample_scenario)

        removed = scenario_manager.remove_scenario('test_scenario')

        assert removed
        assert 'test_scenario' not in scenario_manager.scenarios

    def test_list_scenarios(self, scenario_manager, sample_scenario):
        """Test listing scenarios."""
        scenario_manager.add_scenario(sample_scenario)

        scenarios = scenario_manager.list_scenarios()

        assert len(scenarios) == 1
        assert scenarios[0] == sample_scenario

    def test_create_default_scenarios(self, scenario_manager):
        """Test creating default scenarios."""
        scenario_manager.create_default_scenarios()

        scenarios = scenario_manager.list_scenarios()

        assert len(scenarios) == 3
        assert scenario_manager.get_scenario('base') is not None
        assert scenario_manager.get_scenario('optimistic') is not None
        assert scenario_manager.get_scenario('pessimistic') is not None

    def test_validate_probabilities_valid(self, scenario_manager):
        """Test probability validation with valid probabilities."""
        scenario_manager.create_default_scenarios()

        is_valid = scenario_manager.validate_probabilities()

        assert is_valid

    def test_validate_probabilities_invalid(self, scenario_manager, sample_scenario):
        """Test probability validation with invalid probabilities."""
        sample_scenario.probability = 0.3
        scenario_manager.add_scenario(sample_scenario)

        is_valid = scenario_manager.validate_probabilities()

        assert not is_valid

    def test_normalize_probabilities(self, scenario_manager):
        """Test normalizing probabilities."""
        # Add scenarios with non-normalized probabilities
        for i in range(3):
            macro_adj = MacroeconomicAdjustments()
            scenario = ScenarioConfig(
                name=f'scenario_{i}',
                scenario_type=ScenarioType.BASE,
                probability=1.0,  # All have same probability
                macro_adjustments=macro_adj,
            )
            scenario_manager.add_scenario(scenario)

        scenario_manager.normalize_probabilities()

        # Check that probabilities sum to 1.0
        total = sum(s.probability for s in scenario_manager.scenarios.values())
        assert abs(total - 1.0) < 0.01

        # Each should have 1/3 probability
        for scenario in scenario_manager.scenarios.values():
            assert abs(scenario.probability - 1/3) < 0.01

    def test_load_from_config(self, scenario_manager, tmp_path):
        """Test loading scenarios from config file."""
        # Create temporary config file
        config_content = """
scenarios:
  test_scenario:
    name: test_scenario
    scenario_type: PESSIMISTIC
    probability: 0.5
    description: Test scenario
    macro_adjustments:
      gdp_growth: -2.0
      unemployment_rate: 2.0
    pd_multiplier: 1.3
    lgd_multiplier: 1.2
"""
        config_file = tmp_path / "test_scenarios.yaml"
        config_file.write_text(config_content)

        scenario_manager.load_from_config(str(config_file))

        assert 'test_scenario' in scenario_manager.scenarios
        scenario = scenario_manager.get_scenario('test_scenario')
        assert scenario.probability == 0.5
        assert scenario.pd_multiplier == 1.3

    def test_get_macro_model(self, scenario_manager, sample_scenario):
        """Test getting macro model for scenario."""
        scenario_manager.add_scenario(sample_scenario)

        macro_model = scenario_manager.get_macro_model('test_scenario')

        assert macro_model is not None
        changes = macro_model.get_changes_from_baseline()
        assert changes['gdp_growth'] == -2.0


class TestScenarioWorkflow:
    """Integration tests for complete scenario workflow."""

    @pytest.fixture
    def portfolio_items(self):
        """Load sample portfolio."""
        csv_path = Path(__file__).parent.parent.parent / "examples" / "sample_portfolio.csv"
        if csv_path.exists():
            return PortfolioLoader.load_from_csv(str(csv_path))
        else:
            # Create minimal test portfolio if sample doesn't exist
            from models.portfolio_item import PortfolioItem
            from models.enums import Stage

            return [
                PortfolioItem(
                    item_id="TEST001",
                    borrower_id="BORR001",
                    origination_date=date(2020, 1, 1),
                    maturity_date=date(2025, 1, 1),
                    outstanding_amount=Decimal('1000000'),
                    credit_score=700,
                    current_stage=Stage.STAGE_1,
                )
            ]

    def test_complete_scenario_workflow(self, portfolio_items):
        """Test complete multi-scenario ECL calculation workflow."""
        # Create scenario manager
        scenario_mgr = ScenarioManager()
        scenario_mgr.create_default_scenarios()

        # Create ECL engine
        engine = ECLCalculationEngine()

        # Calculate ECL for each scenario
        scenario_results = {}
        for scenario in scenario_mgr.list_scenarios():
            result = engine.calculate_portfolio_ecl(
                portfolio_items,
                scenario=scenario,
                apply_staging=True
            )
            scenario_results[scenario.name] = result

        # Verify results
        assert len(scenario_results) == 3
        assert 'base' in scenario_results
        assert 'optimistic' in scenario_results
        assert 'pessimistic' in scenario_results

        # Calculate weighted ECL
        weighted_ecl = scenario_mgr.calculate_weighted_ecl(scenario_results)

        assert weighted_ecl > 0

        # Verify ECL ordering (pessimistic > base > optimistic)
        base_ecl = scenario_results['base'].total_ecl
        opt_ecl = scenario_results['optimistic'].total_ecl
        pess_ecl = scenario_results['pessimistic'].total_ecl

        # Note: Due to multipliers, this ordering should generally hold
        assert pess_ecl >= base_ecl
        assert base_ecl >= opt_ecl

    def test_weighted_portfolio_result(self, portfolio_items):
        """Test creating weighted portfolio result."""
        # Create scenarios
        scenario_mgr = ScenarioManager()
        scenario_mgr.create_default_scenarios()

        # Calculate ECL
        engine = ECLCalculationEngine()
        scenario_results = {}
        for scenario in scenario_mgr.list_scenarios():
            result = engine.calculate_portfolio_ecl(
                portfolio_items,
                scenario=scenario
            )
            scenario_results[scenario.name] = result

        # Get weighted result
        weighted_result = scenario_mgr.calculate_weighted_portfolio_result(scenario_results)

        assert weighted_result.total_ecl > 0
        assert weighted_result.scenario_name == 'probability_weighted'

    def test_scenario_comparison(self, portfolio_items):
        """Test scenario comparison."""
        scenario_mgr = ScenarioManager()
        scenario_mgr.create_default_scenarios()

        engine = ECLCalculationEngine()
        scenario_results = {}
        for scenario in scenario_mgr.list_scenarios():
            result = engine.calculate_portfolio_ecl(portfolio_items, scenario=scenario)
            scenario_results[scenario.name] = result

        comparison = scenario_mgr.get_scenario_comparison(scenario_results)

        assert 'scenarios' in comparison
        assert 'weighted_ecl' in comparison
        assert 'min_ecl' in comparison
        assert 'max_ecl' in comparison
        assert comparison['max_ecl'] >= comparison['min_ecl']
