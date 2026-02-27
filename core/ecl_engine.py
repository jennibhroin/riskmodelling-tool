"""Main ECL calculation engine - orchestrates PD, LGD, and EAD calculations."""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from collections import defaultdict

from models.portfolio_item import PortfolioItem
from models.calculation_results import ECLResult, PortfolioECLResult
from models.scenario_config import ScenarioConfig
from models.enums import Stage

from core.probability_of_default import PDCalculator
from core.loss_given_default import LGDCalculator
from core.exposure import EADCalculator
from core.staging_framework import StagingFramework

from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class ECLCalculationEngine:
    """Main engine for calculating Expected Credit Loss (ECL).

    Orchestrates PD, LGD, and EAD calculations according to IFRS 9.
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize ECL calculation engine.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or get_config()

        # Initialize component calculators
        self.pd_calculator = PDCalculator()
        self.lgd_calculator = LGDCalculator()
        self.ead_calculator = EADCalculator()
        self.staging_framework = StagingFramework()

        logger.info("ECL calculation engine initialized")

    def calculate_ecl(
        self,
        item: PortfolioItem,
        scenario: Optional[ScenarioConfig] = None,
        apply_staging: bool = True
    ) -> ECLResult:
        """Calculate ECL for a single portfolio item.

        ECL = PD × LGD × EAD

        Args:
            item: Portfolio item
            scenario: Optional scenario configuration
            apply_staging: Whether to reclassify stage before calculation

        Returns:
            ECL calculation result
        """
        # Reclassify stage if requested
        if apply_staging:
            original_stage = item.current_stage
            pd_12m = self.pd_calculator.calculate_12m_pd(item)
            item.current_stage = self.staging_framework.classify_stage(item, pd_12m)

            if item.current_stage != original_stage:
                logger.debug(
                    "Stage reclassified",
                    item_id=item.item_id,
                    from_stage=str(original_stage),
                    to_stage=str(item.current_stage)
                )

        # Determine if Stage 1 (12-month) or Stage 2/3 (lifetime)
        if item.current_stage == Stage.STAGE_1:
            return self.calculate_stage_1_ecl(item, scenario)
        else:
            return self.calculate_stage_2_3_ecl(item, scenario)

    def calculate_stage_1_ecl(
        self,
        item: PortfolioItem,
        scenario: Optional[ScenarioConfig] = None
    ) -> ECLResult:
        """Calculate 12-month ECL for Stage 1 item.

        Args:
            item: Portfolio item (must be Stage 1)
            scenario: Optional scenario configuration

        Returns:
            ECL calculation result
        """
        # Calculate 12-month PD
        pd = self.pd_calculator.calculate_12m_pd(item)

        # Apply scenario adjustment to PD
        if scenario:
            pd = self.pd_calculator.apply_scenario_adjustment(
                pd,
                scenario.pd_multiplier
            )

        # Calculate EAD
        ead = self.ead_calculator.calculate_current_ead(item)

        # Apply scenario adjustment to EAD
        if scenario:
            ead = self.ead_calculator.calculate_ead_with_scenario_adjustment(
                item,
                scenario.ead_multiplier
            )

        # Calculate LGD
        lgd = self.lgd_calculator.calculate_lgd(item, ead)

        # Apply scenario adjustment to LGD
        if scenario:
            lgd = self.lgd_calculator.apply_scenario_adjustment(
                lgd,
                scenario.lgd_multiplier,
                scenario.lgd_downturn_factor
            )

        # Calculate ECL
        ecl_amount = ead * Decimal(str(pd)) * Decimal(str(lgd))

        # Create result
        result = ECLResult(
            item_id=item.item_id,
            stage=Stage.STAGE_1,
            probability_of_default=pd,
            loss_given_default=lgd,
            exposure_at_default=ead,
            ecl_amount=ecl_amount,
            time_horizon_months=12,
            scenario_name=scenario.name if scenario else None,
            scenario_type=scenario.scenario_type if scenario else None,
            collateral_value=item.collateral_value,
            unsecured_exposure=self.lgd_calculator._calculate_unsecured_exposure(item, ead),
        )

        logger.debug(
            "Calculated Stage 1 ECL",
            item_id=item.item_id,
            pd=pd,
            lgd=lgd,
            ead=float(ead),
            ecl=float(ecl_amount)
        )

        return result

    def calculate_stage_2_3_ecl(
        self,
        item: PortfolioItem,
        scenario: Optional[ScenarioConfig] = None
    ) -> ECLResult:
        """Calculate lifetime ECL for Stage 2/3 item.

        Args:
            item: Portfolio item (must be Stage 2 or 3)
            scenario: Optional scenario configuration

        Returns:
            ECL calculation result
        """
        # Calculate lifetime PD
        lifetime_pd = self.pd_calculator.calculate_lifetime_pd(item)

        # Apply scenario adjustment to PD
        if scenario:
            lifetime_pd = self.pd_calculator.apply_scenario_adjustment(
                lifetime_pd,
                scenario.pd_multiplier
            )

        # Calculate EAD
        ead = self.ead_calculator.calculate_current_ead(item)

        # Apply scenario adjustment to EAD
        if scenario:
            ead = self.ead_calculator.calculate_ead_with_scenario_adjustment(
                item,
                scenario.ead_multiplier
            )

        # Calculate LGD with downturn adjustment for Stage 2/3
        lgd = self.lgd_calculator.calculate_lgd(
            item,
            ead,
            apply_downturn=(item.current_stage == Stage.STAGE_2)
        )

        # Apply scenario adjustment to LGD
        if scenario:
            lgd = self.lgd_calculator.apply_scenario_adjustment(
                lgd,
                scenario.lgd_multiplier,
                scenario.lgd_downturn_factor
            )

        # For detailed lifetime ECL, get marginal PDs
        remaining_months = item.remaining_term_months
        marginal_pds, cumulative_pds = self.pd_calculator.get_lifetime_pd_curve(item)

        # Apply scenario adjustment to marginal PDs if needed
        if scenario:
            marginal_pds = [pd * scenario.pd_multiplier for pd in marginal_pds]

        # Calculate period ECL (simplified - same EAD and LGD for all periods)
        period_ecl = [
            ead * Decimal(str(mpd)) * Decimal(str(lgd))
            for mpd in marginal_pds
        ]

        # Total lifetime ECL
        ecl_amount = sum(period_ecl) if period_ecl else Decimal('0')

        # Create result
        result = ECLResult(
            item_id=item.item_id,
            stage=item.current_stage,
            probability_of_default=lifetime_pd,
            loss_given_default=lgd,
            exposure_at_default=ead,
            ecl_amount=ecl_amount,
            time_horizon_months=remaining_months,
            scenario_name=scenario.name if scenario else None,
            scenario_type=scenario.scenario_type if scenario else None,
            collateral_value=item.collateral_value,
            unsecured_exposure=self.lgd_calculator._calculate_unsecured_exposure(item, ead),
            period_ecl=period_ecl if period_ecl else None,
            period_pd=marginal_pds if marginal_pds else None,
        )

        logger.debug(
            "Calculated Stage 2/3 ECL",
            item_id=item.item_id,
            stage=str(item.current_stage),
            lifetime_pd=lifetime_pd,
            lgd=lgd,
            ead=float(ead),
            ecl=float(ecl_amount)
        )

        return result

    def calculate_portfolio_ecl(
        self,
        items: List[PortfolioItem],
        scenario: Optional[ScenarioConfig] = None,
        apply_staging: bool = True
    ) -> PortfolioECLResult:
        """Calculate ECL for entire portfolio.

        Args:
            items: List of portfolio items
            scenario: Optional scenario configuration
            apply_staging: Whether to reclassify stages before calculation

        Returns:
            Portfolio ECL result
        """
        logger.info(
            "Calculating portfolio ECL",
            item_count=len(items),
            scenario=scenario.name if scenario else "base"
        )

        # Calculate ECL for each item
        item_results = []
        for item in items:
            try:
                result = self.calculate_ecl(item, scenario, apply_staging)
                item_results.append(result)
            except Exception as e:
                logger.error(
                    "Failed to calculate ECL for item",
                    item_id=item.item_id,
                    error=str(e)
                )
                # Continue with other items

        # Aggregate results
        portfolio_result = self._aggregate_results(
            item_results,
            scenario,
            items
        )

        logger.info(
            "Portfolio ECL calculated",
            total_ecl=float(portfolio_result.total_ecl),
            total_exposure=float(portfolio_result.total_exposure),
            coverage_ratio=portfolio_result.coverage_ratio
        )

        return portfolio_result

    def _aggregate_results(
        self,
        item_results: List[ECLResult],
        scenario: Optional[ScenarioConfig],
        items: List[PortfolioItem]
    ) -> PortfolioECLResult:
        """Aggregate individual ECL results into portfolio result.

        Args:
            item_results: List of individual ECL results
            scenario: Scenario configuration (if any)
            items: Original portfolio items

        Returns:
            Aggregated portfolio ECL result
        """
        # Initialize aggregations
        total_ecl = Decimal('0')
        total_exposure = Decimal('0')

        stage_ecl = {Stage.STAGE_1: Decimal('0'), Stage.STAGE_2: Decimal('0'), Stage.STAGE_3: Decimal('0')}
        stage_exposure = {Stage.STAGE_1: Decimal('0'), Stage.STAGE_2: Decimal('0'), Stage.STAGE_3: Decimal('0')}
        stage_count = {Stage.STAGE_1: 0, Stage.STAGE_2: 0, Stage.STAGE_3: 0}

        ecl_by_sector = defaultdict(Decimal)
        ecl_by_product = defaultdict(Decimal)

        # Create item lookup
        item_lookup = {item.item_id: item for item in items}

        # Aggregate
        for result in item_results:
            total_ecl += result.ecl_amount
            total_exposure += result.exposure_at_default

            stage_ecl[result.stage] += result.ecl_amount
            stage_exposure[result.stage] += result.exposure_at_default
            stage_count[result.stage] += 1

            # Get item for sector/product
            item = item_lookup.get(result.item_id)
            if item:
                ecl_by_sector[item.sector] += result.ecl_amount
                ecl_by_product[item.product_type] += result.ecl_amount

        # Create portfolio result
        portfolio_result = PortfolioECLResult(
            total_ecl=total_ecl,
            total_exposure=total_exposure,
            total_items=len(item_results),
            stage_1_ecl=stage_ecl[Stage.STAGE_1],
            stage_2_ecl=stage_ecl[Stage.STAGE_2],
            stage_3_ecl=stage_ecl[Stage.STAGE_3],
            stage_1_exposure=stage_exposure[Stage.STAGE_1],
            stage_2_exposure=stage_exposure[Stage.STAGE_2],
            stage_3_exposure=stage_exposure[Stage.STAGE_3],
            stage_1_count=stage_count[Stage.STAGE_1],
            stage_2_count=stage_count[Stage.STAGE_2],
            stage_3_count=stage_count[Stage.STAGE_3],
            item_results=item_results,
            ecl_by_sector=dict(ecl_by_sector),
            ecl_by_product=dict(ecl_by_product),
            scenario_name=scenario.name if scenario else None,
            scenario_type=scenario.scenario_type if scenario else None,
            scenario_probability=scenario.probability if scenario else None,
            calculation_date=date.today().isoformat(),
        )

        return portfolio_result
