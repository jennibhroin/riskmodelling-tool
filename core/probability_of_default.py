"""Probability of Default (PD) calculations."""

import math
from typing import List, Optional, Tuple

from models.portfolio_item import PortfolioItem
from models.enums import Stage
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class PDCalculator:
    """Calculate Probability of Default (PD) for credit exposures."""

    def __init__(self, config: Optional[dict] = None):
        """Initialize PD calculator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or get_config().get_section('pd')

    def calculate_12m_pd(
        self,
        item: PortfolioItem,
        base_pd_override: Optional[float] = None
    ) -> float:
        """Calculate 12-month PD.

        Args:
            item: Portfolio item
            base_pd_override: Optional base PD override

        Returns:
            12-month PD (as decimal, e.g., 0.02 = 2%)
        """
        if base_pd_override is not None:
            pd = base_pd_override
        else:
            pd = self._credit_score_to_pd(item.credit_score)

        # Apply adjustments based on performance
        pd = self._adjust_pd_for_performance(pd, item)

        # Apply floor and ceiling
        pd = self._apply_bounds(pd)

        logger.debug(
            "Calculated 12-month PD",
            item_id=item.item_id,
            credit_score=item.credit_score,
            pd=pd
        )

        return pd

    def calculate_lifetime_pd(
        self,
        item: PortfolioItem,
        base_pd_override: Optional[float] = None
    ) -> float:
        """Calculate lifetime PD (cumulative PD to maturity).

        Args:
            item: Portfolio item
            base_pd_override: Optional base PD override

        Returns:
            Lifetime cumulative PD
        """
        # Get 12-month PD
        pd_12m = self.calculate_12m_pd(item, base_pd_override)

        # Get remaining term
        remaining_months = item.remaining_term_months
        if remaining_months <= 12:
            return pd_12m

        # Calculate cumulative PD using marginal PDs
        marginal_pds = self.get_marginal_pd_curve(item, pd_12m, remaining_months)
        cumulative_pd = self._calculate_cumulative_pd(marginal_pds)

        logger.debug(
            "Calculated lifetime PD",
            item_id=item.item_id,
            pd_12m=pd_12m,
            remaining_months=remaining_months,
            lifetime_pd=cumulative_pd
        )

        return cumulative_pd

    def get_marginal_pd_curve(
        self,
        item: PortfolioItem,
        pd_12m: float,
        horizon_months: int
    ) -> List[float]:
        """Get marginal PD for each month in horizon.

        Args:
            item: Portfolio item
            pd_12m: 12-month PD
            horizon_months: Projection horizon in months

        Returns:
            List of monthly marginal PDs
        """
        # Get monthly default rate from config
        term_structure = self.config.get('term_structure', {})

        if item.current_stage == Stage.STAGE_1:
            monthly_rate = term_structure.get('stage_1_monthly_rate', 0.08)
        elif item.current_stage == Stage.STAGE_2:
            monthly_rate = term_structure.get('stage_2_monthly_rate', 0.12)
        else:  # Stage 3
            monthly_rate = term_structure.get('stage_3_monthly_rate', 0.20)

        # Calculate marginal PDs
        marginal_pds = []
        survival_prob = 1.0

        for month in range(min(horizon_months, item.remaining_term_months)):
            # Marginal PD = survival_prob × monthly_rate
            marginal_pd = survival_prob * monthly_rate * pd_12m / 0.01  # Scale by PD level

            # Cap marginal PD
            marginal_pd = min(marginal_pd, survival_prob)

            marginal_pds.append(marginal_pd)

            # Update survival probability
            survival_prob -= marginal_pd

            # Stop if survival probability becomes too low
            if survival_prob < 0.01:
                break

        return marginal_pds

    def get_lifetime_pd_curve(
        self,
        item: PortfolioItem,
        base_pd_override: Optional[float] = None
    ) -> Tuple[List[float], List[float]]:
        """Get full PD curve (marginal and cumulative) to maturity.

        Args:
            item: Portfolio item
            base_pd_override: Optional base PD override

        Returns:
            Tuple of (marginal_pds, cumulative_pds)
        """
        pd_12m = self.calculate_12m_pd(item, base_pd_override)
        remaining_months = item.remaining_term_months

        marginal_pds = self.get_marginal_pd_curve(item, pd_12m, remaining_months)

        # Calculate cumulative PDs
        cumulative_pds = []
        survival_prob = 1.0

        for marginal_pd in marginal_pds:
            survival_prob -= marginal_pd
            cumulative_pd = 1.0 - survival_prob
            cumulative_pds.append(cumulative_pd)

        return marginal_pds, cumulative_pds

    def calculate_marginal_default_probability(
        self,
        period_start_survival: float,
        period_end_survival: float
    ) -> float:
        """Calculate marginal default probability for a period.

        Args:
            period_start_survival: Survival probability at start
            period_end_survival: Survival probability at end

        Returns:
            Marginal default probability
        """
        return period_start_survival - period_end_survival

    def _credit_score_to_pd(self, credit_score: int) -> float:
        """Convert credit score to 12-month PD.

        Uses a logistic function to map credit scores to PD.

        Args:
            credit_score: Credit score (300-850)

        Returns:
            12-month PD
        """
        # Normalize credit score to 0-1 range
        score_min = self.config.get('credit_score_min', 300)
        score_max = self.config.get('credit_score_max', 850)

        normalized_score = (credit_score - score_min) / (score_max - score_min)
        normalized_score = max(0, min(1, normalized_score))

        # Logistic function: PD decreases as score increases
        # At score 300: PD ≈ 20%
        # At score 850: PD ≈ 0.1%
        k = 10  # Steepness parameter
        midpoint = 0.5  # Midpoint at score 575

        pd = 0.20 / (1 + math.exp(k * (normalized_score - midpoint)))

        return pd

    def _adjust_pd_for_performance(self, pd: float, item: PortfolioItem) -> float:
        """Adjust PD based on performance indicators.

        Args:
            pd: Base PD
            item: Portfolio item

        Returns:
            Adjusted PD
        """
        adjustment = 1.0

        # Days past due adjustment
        if item.days_past_due > 0:
            if item.days_past_due <= 30:
                adjustment *= 1.5  # 50% increase
            elif item.days_past_due <= 60:
                adjustment *= 2.0  # 100% increase
            elif item.days_past_due <= 90:
                adjustment *= 3.0  # 200% increase
            else:
                adjustment *= 5.0  # 400% increase

        # Times past due in last 12 months
        if item.times_past_due_12m > 0:
            adjustment *= (1 + 0.2 * item.times_past_due_12m)

        # Forbearance/restructuring
        if item.is_forborne or item.is_restructured:
            adjustment *= 1.5

        return pd * adjustment

    def _apply_bounds(self, pd: float) -> float:
        """Apply floor and ceiling to PD.

        Args:
            pd: PD value

        Returns:
            Bounded PD
        """
        floor = self.config.get('floor', 0.0001)
        ceiling = self.config.get('ceiling', 0.99)

        return max(floor, min(ceiling, pd))

    def _calculate_cumulative_pd(self, marginal_pds: List[float]) -> float:
        """Calculate cumulative PD from marginal PDs.

        Args:
            marginal_pds: List of monthly marginal PDs

        Returns:
            Cumulative PD
        """
        survival_prob = 1.0

        for marginal_pd in marginal_pds:
            survival_prob -= marginal_pd

        return 1.0 - survival_prob

    def apply_scenario_adjustment(
        self,
        base_pd: float,
        scenario_multiplier: float
    ) -> float:
        """Apply scenario-specific adjustment to PD.

        Args:
            base_pd: Base PD
            scenario_multiplier: Scenario multiplier (e.g., 1.3 for pessimistic)

        Returns:
            Adjusted PD
        """
        adjusted_pd = base_pd * scenario_multiplier
        adjusted_pd = self._apply_bounds(adjusted_pd)

        return adjusted_pd
