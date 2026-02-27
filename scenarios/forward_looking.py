"""Forward-looking adjustments to PD and LGD based on macroeconomic scenarios."""

from typing import Dict, Optional

from models.portfolio_item import PortfolioItem
from scenarios.macroeconomic_model import MacroeconomicModel
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class ForwardLookingAdjustment:
    """Apply forward-looking adjustments to PD and LGD based on macro scenarios.

    Uses elasticity-based approach where:
    - PD adjustment = PD_base × (1 + Σ(elasticity × macro_change))
    - LGD adjustment = LGD_base × (1 + Σ(elasticity × macro_change))
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize forward-looking adjustment calculator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or get_config().get_section('macro_variables')

        # Get elasticities from config
        self.pd_elasticities = self.config.get('pd_elasticities', {
            'gdp_growth': -0.15,  # 1% GDP decline increases PD by 15%
            'unemployment_rate': 0.10,  # 1% unemployment increase raises PD by 10%
            'credit_spreads': 0.05,  # 100 bps spread increase raises PD by 5%
        })

        self.lgd_elasticities = self.config.get('lgd_elasticities', {
            'house_price_index': -0.20,  # 10% house price decline increases LGD by 2%
            'unemployment_rate': 0.08,  # 1% unemployment increase raises LGD by 8%
        })

        logger.info(
            "Forward-looking adjustment initialized",
            pd_elasticities=self.pd_elasticities,
            lgd_elasticities=self.lgd_elasticities
        )

    def adjust_pd(
        self,
        base_pd: float,
        macro_model: MacroeconomicModel,
        item: Optional[PortfolioItem] = None
    ) -> float:
        """Adjust PD based on macroeconomic changes.

        PD_adjusted = PD_base × (1 + Σ(elasticity × macro_change))

        Args:
            base_pd: Base probability of default
            macro_model: Macroeconomic model with current scenario
            item: Optional portfolio item for sector-specific adjustments

        Returns:
            Adjusted PD
        """
        # Get macro changes from baseline
        macro_changes = macro_model.get_changes_from_baseline()

        # Calculate adjustment factor
        adjustment_factor = 0.0

        for variable, elasticity in self.pd_elasticities.items():
            if variable in macro_changes:
                change = macro_changes[variable]

                # Normalize certain variables
                if variable == 'credit_spreads':
                    # Credit spreads in bps, normalize to percentage points
                    change = change / 100.0

                contribution = elasticity * change
                adjustment_factor += contribution

                logger.debug(
                    "PD adjustment contribution",
                    variable=variable,
                    change=change,
                    elasticity=elasticity,
                    contribution=contribution
                )

        # Apply sector-specific multiplier if available
        sector_multiplier = 1.0
        if item:
            sector_multiplier = self._get_sector_sensitivity(item.sector)

        # Calculate adjusted PD
        adjusted_pd = base_pd * (1 + adjustment_factor * sector_multiplier)

        # Apply bounds (PD should be between 0 and 1)
        adjusted_pd = max(0.0001, min(0.99, adjusted_pd))

        logger.debug(
            "PD adjusted",
            base_pd=base_pd,
            adjustment_factor=adjustment_factor,
            sector_multiplier=sector_multiplier,
            adjusted_pd=adjusted_pd
        )

        return adjusted_pd

    def adjust_lgd(
        self,
        base_lgd: float,
        macro_model: MacroeconomicModel,
        item: Optional[PortfolioItem] = None
    ) -> float:
        """Adjust LGD based on macroeconomic changes.

        LGD_adjusted = LGD_base × (1 + Σ(elasticity × macro_change))

        Args:
            base_lgd: Base loss given default
            macro_model: Macroeconomic model with current scenario
            item: Optional portfolio item for collateral-specific adjustments

        Returns:
            Adjusted LGD
        """
        # Get macro changes from baseline
        macro_changes = macro_model.get_changes_from_baseline()

        # Calculate adjustment factor
        adjustment_factor = 0.0

        for variable, elasticity in self.lgd_elasticities.items():
            if variable in macro_changes:
                change = macro_changes[variable]

                # Normalize certain variables
                if variable == 'house_price_index':
                    # House price index change is in percentage points
                    change = change / 100.0

                contribution = elasticity * change
                adjustment_factor += contribution

                logger.debug(
                    "LGD adjustment contribution",
                    variable=variable,
                    change=change,
                    elasticity=elasticity,
                    contribution=contribution
                )

        # Apply collateral-specific multiplier if available
        collateral_multiplier = 1.0
        if item and item.collateral_type:
            collateral_multiplier = self._get_collateral_sensitivity(item.collateral_type)

        # Calculate adjusted LGD
        adjusted_lgd = base_lgd * (1 + adjustment_factor * collateral_multiplier)

        # Apply bounds (LGD should be between 0 and 1)
        adjusted_lgd = max(0.01, min(1.0, adjusted_lgd))

        logger.debug(
            "LGD adjusted",
            base_lgd=base_lgd,
            adjustment_factor=adjustment_factor,
            collateral_multiplier=collateral_multiplier,
            adjusted_lgd=adjusted_lgd
        )

        return adjusted_lgd

    def adjust_ead(
        self,
        base_ead: float,
        macro_model: MacroeconomicModel,
        ccf_adjustment: float = 0.0
    ) -> float:
        """Adjust EAD based on macroeconomic scenario.

        In stress scenarios, undrawn commitments may be drawn more heavily.

        Args:
            base_ead: Base exposure at default
            macro_model: Macroeconomic model with current scenario
            ccf_adjustment: Additional CCF adjustment in stress

        Returns:
            Adjusted EAD
        """
        # Get macro changes
        macro_changes = macro_model.get_changes_from_baseline()

        # Calculate stress factor based on GDP and unemployment
        stress_factor = 0.0

        if 'gdp_growth' in macro_changes:
            # Negative GDP growth increases drawdowns
            gdp_change = macro_changes['gdp_growth']
            if gdp_change < 0:
                stress_factor += abs(gdp_change) * 0.02  # 2% per percentage point decline

        if 'unemployment_rate' in macro_changes:
            # Rising unemployment increases drawdowns
            unemp_change = macro_changes['unemployment_rate']
            if unemp_change > 0:
                stress_factor += unemp_change * 0.015  # 1.5% per percentage point increase

        # Apply adjustment
        adjustment_factor = 1.0 + stress_factor + ccf_adjustment
        adjusted_ead = base_ead * adjustment_factor

        logger.debug(
            "EAD adjusted",
            base_ead=base_ead,
            stress_factor=stress_factor,
            ccf_adjustment=ccf_adjustment,
            adjusted_ead=adjusted_ead
        )

        return adjusted_ead

    def _get_sector_sensitivity(self, sector: str) -> float:
        """Get sector-specific sensitivity multiplier for PD adjustments.

        Args:
            sector: Sector name

        Returns:
            Sensitivity multiplier (1.0 = average, >1.0 = more sensitive)
        """
        # Sector sensitivity to economic cycles
        sector_sensitivities = {
            'Construction': 1.5,
            'Hospitality': 1.4,
            'Retail': 1.3,
            'Transportation': 1.2,
            'Manufacturing': 1.1,
            'Energy': 1.1,
            'Real Estate': 1.0,
            'Technology': 0.9,
            'Healthcare': 0.8,
            'Financial Services': 1.0,
            'Utilities': 0.7,
        }

        return sector_sensitivities.get(sector, 1.0)

    def _get_collateral_sensitivity(self, collateral_type: str) -> float:
        """Get collateral-specific sensitivity multiplier for LGD adjustments.

        Args:
            collateral_type: Collateral type

        Returns:
            Sensitivity multiplier (1.0 = average, >1.0 = more sensitive)
        """
        # Collateral sensitivity to economic stress
        collateral_sensitivities = {
            'real_estate': 1.3,  # Highly sensitive to house prices
            'inventory': 1.4,  # Sensitive to demand
            'equipment': 1.1,
            'receivables': 1.2,
            'securities': 1.5,  # Highly sensitive to markets
            'cash': 0.0,  # Not sensitive
        }

        collateral_lower = collateral_type.lower().replace(' ', '_')
        return collateral_sensitivities.get(collateral_lower, 1.0)

    def calculate_scenario_multipliers(
        self,
        macro_model: MacroeconomicModel
    ) -> Dict[str, float]:
        """Calculate overall scenario multipliers for PD, LGD, and EAD.

        Args:
            macro_model: Macroeconomic model with scenario

        Returns:
            Dictionary with 'pd_multiplier', 'lgd_multiplier', 'ead_multiplier'
        """
        # Use a representative base PD and LGD to calculate multipliers
        base_pd = 0.02  # 2%
        base_lgd = 0.45  # 45%
        base_ead = 1.0

        adjusted_pd = self.adjust_pd(base_pd, macro_model)
        adjusted_lgd = self.adjust_lgd(base_lgd, macro_model)
        adjusted_ead = self.adjust_ead(base_ead, macro_model)

        multipliers = {
            'pd_multiplier': adjusted_pd / base_pd,
            'lgd_multiplier': adjusted_lgd / base_lgd,
            'ead_multiplier': adjusted_ead / base_ead,
        }

        logger.info(
            "Calculated scenario multipliers",
            multipliers=multipliers,
            macro_changes=macro_model.get_changes_from_baseline()
        )

        return multipliers
