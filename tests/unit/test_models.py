"""Unit tests for data models."""

import pytest
from datetime import date
from decimal import Decimal

from models.enums import Stage, ScenarioType, CalculationMethod
from models.portfolio_item import PortfolioItem
from models.scenario_config import ScenarioConfig, MacroeconomicAdjustments
from models.calculation_results import ECLResult, PortfolioECLResult


class TestStageEnum:
    """Tests for Stage enumeration."""

    def test_stage_values(self):
        """Test stage enum values."""
        assert Stage.STAGE_1.value == "Stage 1"
        assert Stage.STAGE_2.value == "Stage 2"
        assert Stage.STAGE_3.value == "Stage 3"

    def test_stage_string_conversion(self):
        """Test stage string conversion."""
        assert str(Stage.STAGE_1) == "Stage 1"
        assert str(Stage.STAGE_2) == "Stage 2"

    def test_is_performing(self):
        """Test is_performing property."""
        assert Stage.STAGE_1.is_performing
        assert Stage.STAGE_2.is_performing
        assert not Stage.STAGE_3.is_performing

    def test_is_impaired(self):
        """Test is_impaired property."""
        assert not Stage.STAGE_1.is_impaired
        assert not Stage.STAGE_2.is_impaired
        assert Stage.STAGE_3.is_impaired

    def test_uses_lifetime_ecl(self):
        """Test uses_lifetime_ecl property."""
        assert not Stage.STAGE_1.uses_lifetime_ecl
        assert Stage.STAGE_2.uses_lifetime_ecl
        assert Stage.STAGE_3.uses_lifetime_ecl


class TestScenarioTypeEnum:
    """Tests for ScenarioType enumeration."""

    def test_scenario_type_values(self):
        """Test scenario type enum values."""
        assert ScenarioType.BASE.value == "base"
        assert ScenarioType.OPTIMISTIC.value == "optimistic"
        assert ScenarioType.PESSIMISTIC.value == "pessimistic"
        assert ScenarioType.STRESS.value == "stress"


class TestCalculationMethodEnum:
    """Tests for CalculationMethod enumeration."""

    def test_calculation_method_values(self):
        """Test calculation method enum values."""
        assert CalculationMethod.INDIVIDUAL.value == "individual"
        assert CalculationMethod.COHORT.value == "cohort"
        assert CalculationMethod.VINTAGE.value == "vintage"


class TestPortfolioItem:
    """Tests for PortfolioItem data model."""

    @pytest.fixture
    def sample_item(self):
        """Create sample portfolio item."""
        return PortfolioItem(
            item_id="LOAN001",
            borrower_id="BORR001",
            origination_date=date(2020, 1, 15),
            maturity_date=date(2025, 1, 15),
            reporting_date=date(2023, 6, 30),
            outstanding_amount=Decimal('1000000'),
            undrawn_commitment=Decimal('500000'),
            interest_rate=5.5,
            sector="Manufacturing",
            collateral_value=Decimal('800000'),
            credit_score=720,
            days_past_due=0,
            current_stage=Stage.STAGE_1,
        )

    def test_portfolio_item_creation(self, sample_item):
        """Test basic portfolio item creation."""
        assert sample_item.item_id == "LOAN001"
        assert sample_item.outstanding_amount == Decimal('1000000')
        assert sample_item.current_stage == Stage.STAGE_1

    def test_total_exposure(self, sample_item):
        """Test total exposure calculation."""
        expected = Decimal('1500000')
        assert sample_item.total_exposure == expected

    def test_loan_to_value(self, sample_item):
        """Test loan-to-value ratio."""
        expected = 1000000 / 800000
        assert sample_item.loan_to_value == pytest.approx(expected)

    def test_loan_to_value_no_collateral(self):
        """Test LTV with no collateral."""
        item = PortfolioItem(
            item_id="LOAN002",
            borrower_id="BORR002",
            origination_date=date(2020, 1, 1),
            maturity_date=date(2025, 1, 1),
            outstanding_amount=Decimal('100000'),
            collateral_value=Decimal('0'),
        )
        assert item.loan_to_value == float('inf')

    def test_remaining_term_months(self, sample_item):
        """Test remaining term calculation."""
        # From 2023-06-30 to 2025-01-15 is approximately 18.5 months
        assert 18 <= sample_item.remaining_term_months <= 19

    def test_age_months(self, sample_item):
        """Test loan age calculation."""
        # From 2020-01-15 to 2023-06-30 is approximately 41.5 months
        assert 41 <= sample_item.age_months <= 42

    def test_is_past_due(self, sample_item):
        """Test past due flag."""
        assert not sample_item.is_past_due
        sample_item.days_past_due = 10
        assert sample_item.is_past_due

    def test_is_defaulted(self, sample_item):
        """Test default detection."""
        assert not sample_item.is_defaulted

        # Test DPD-based default
        sample_item.days_past_due = 100
        assert sample_item.is_defaulted

        # Test stage-based default
        sample_item.days_past_due = 0
        sample_item.current_stage = Stage.STAGE_3
        assert sample_item.is_defaulted

    def test_string_date_conversion(self):
        """Test automatic date string conversion."""
        item = PortfolioItem(
            item_id="LOAN003",
            borrower_id="BORR003",
            origination_date="2020-01-15",
            maturity_date="2025-01-15",
            outstanding_amount=Decimal('100000'),
        )
        assert isinstance(item.origination_date, date)
        assert item.origination_date == date(2020, 1, 15)

    def test_string_stage_conversion(self):
        """Test automatic stage string conversion."""
        item = PortfolioItem(
            item_id="LOAN004",
            borrower_id="BORR004",
            origination_date=date(2020, 1, 1),
            maturity_date=date(2025, 1, 1),
            outstanding_amount=Decimal('100000'),
            current_stage="Stage 2",
        )
        assert item.current_stage == Stage.STAGE_2

    def test_to_dict(self, sample_item):
        """Test dictionary conversion."""
        result = sample_item.to_dict()
        assert result['item_id'] == "LOAN001"
        assert result['outstanding_amount'] == 1000000.0
        assert result['current_stage'] == "Stage 1"


class TestMacroeconomicAdjustments:
    """Tests for MacroeconomicAdjustments."""

    def test_default_values(self):
        """Test default adjustment values."""
        adj = MacroeconomicAdjustments()
        assert adj.gdp_growth == 0.0
        assert adj.unemployment_rate == 0.0

    def test_custom_values(self):
        """Test custom adjustment values."""
        adj = MacroeconomicAdjustments(
            gdp_growth=-2.0,
            unemployment_rate=2.0,
            credit_spreads=100,
        )
        assert adj.gdp_growth == -2.0
        assert adj.unemployment_rate == 2.0
        assert adj.credit_spreads == 100

    def test_to_dict(self):
        """Test dictionary conversion."""
        adj = MacroeconomicAdjustments(gdp_growth=1.5)
        result = adj.to_dict()
        assert result['gdp_growth'] == 1.5
        assert 'unemployment_rate' in result


class TestScenarioConfig:
    """Tests for ScenarioConfig."""

    def test_scenario_config_creation(self):
        """Test basic scenario config creation."""
        config = ScenarioConfig(
            name="base",
            scenario_type=ScenarioType.BASE,
            probability=0.5,
        )
        assert config.name == "base"
        assert config.scenario_type == ScenarioType.BASE
        assert config.probability == 0.5

    def test_invalid_probability(self):
        """Test validation of probability bounds."""
        with pytest.raises(ValueError):
            ScenarioConfig(
                name="invalid",
                scenario_type=ScenarioType.BASE,
                probability=1.5,
            )

    def test_invalid_projection_horizon(self):
        """Test validation of projection horizon."""
        with pytest.raises(ValueError):
            ScenarioConfig(
                name="invalid",
                scenario_type=ScenarioType.BASE,
                projection_horizon_months=0,
            )

    def test_to_dict(self):
        """Test dictionary conversion."""
        config = ScenarioConfig(
            name="pessimistic",
            scenario_type=ScenarioType.PESSIMISTIC,
            probability=0.25,
        )
        result = config.to_dict()
        assert result['name'] == "pessimistic"
        assert result['scenario_type'] == "pessimistic"
        assert result['probability'] == 0.25

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'name': 'optimistic',
            'scenario_type': 'optimistic',
            'probability': 0.25,
            'macro_adjustments': {
                'gdp_growth': 1.5,
                'unemployment_rate': -1.0,
            },
        }
        config = ScenarioConfig.from_dict(data)
        assert config.name == 'optimistic'
        assert config.macro_adjustments.gdp_growth == 1.5


class TestECLResult:
    """Tests for ECLResult."""

    @pytest.fixture
    def sample_result(self):
        """Create sample ECL result."""
        return ECLResult(
            item_id="LOAN001",
            stage=Stage.STAGE_1,
            probability_of_default=0.02,
            loss_given_default=0.45,
            exposure_at_default=Decimal('1000000'),
            ecl_amount=Decimal('9000'),
            time_horizon_months=12,
        )

    def test_ecl_result_creation(self, sample_result):
        """Test basic ECL result creation."""
        assert sample_result.item_id == "LOAN001"
        assert sample_result.probability_of_default == 0.02
        assert sample_result.ecl_amount == Decimal('9000')

    def test_ecl_rate(self, sample_result):
        """Test ECL rate calculation."""
        expected = 9000 / 1000000
        assert sample_result.ecl_rate == pytest.approx(expected)

    def test_coverage_ratio(self, sample_result):
        """Test coverage ratio."""
        assert sample_result.coverage_ratio == pytest.approx(0.009)

    def test_to_dict(self, sample_result):
        """Test dictionary conversion."""
        result = sample_result.to_dict()
        assert result['item_id'] == "LOAN001"
        assert result['ecl_amount'] == 9000.0


class TestPortfolioECLResult:
    """Tests for PortfolioECLResult."""

    @pytest.fixture
    def sample_portfolio_result(self):
        """Create sample portfolio ECL result."""
        return PortfolioECLResult(
            total_ecl=Decimal('100000'),
            total_exposure=Decimal('10000000'),
            total_items=100,
            stage_1_ecl=Decimal('30000'),
            stage_2_ecl=Decimal('50000'),
            stage_3_ecl=Decimal('20000'),
            stage_1_exposure=Decimal('7000000'),
            stage_2_exposure=Decimal('2500000'),
            stage_3_exposure=Decimal('500000'),
            stage_1_count=70,
            stage_2_count=25,
            stage_3_count=5,
        )

    def test_portfolio_result_creation(self, sample_portfolio_result):
        """Test basic portfolio result creation."""
        assert sample_portfolio_result.total_ecl == Decimal('100000')
        assert sample_portfolio_result.total_items == 100

    def test_coverage_ratio(self, sample_portfolio_result):
        """Test overall coverage ratio."""
        expected = 100000 / 10000000
        assert sample_portfolio_result.coverage_ratio == pytest.approx(expected)

    def test_stage_coverage_ratios(self, sample_portfolio_result):
        """Test stage-specific coverage ratios."""
        assert sample_portfolio_result.stage_1_coverage == pytest.approx(30000 / 7000000)
        assert sample_portfolio_result.stage_2_coverage == pytest.approx(50000 / 2500000)
        assert sample_portfolio_result.stage_3_coverage == pytest.approx(20000 / 500000)

    def test_stage_ratios(self, sample_portfolio_result):
        """Test stage exposure ratios."""
        assert sample_portfolio_result.stage_2_ratio == pytest.approx(2500000 / 10000000)
        assert sample_portfolio_result.stage_3_ratio == pytest.approx(500000 / 10000000)

    def test_get_summary(self, sample_portfolio_result):
        """Test summary statistics."""
        summary = sample_portfolio_result.get_summary()
        assert summary['total_ecl'] == 100000.0
        assert summary['total_items'] == 100
        assert 'stage_1' in summary
        assert 'stage_2' in summary
        assert 'stage_3' in summary

    def test_to_dict(self, sample_portfolio_result):
        """Test dictionary conversion."""
        result = sample_portfolio_result.to_dict()
        assert result['total_ecl'] == 100000.0
        assert result['total_items'] == 100
