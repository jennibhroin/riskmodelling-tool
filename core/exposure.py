"""Exposure at Default (EAD) calculations."""

from decimal import Decimal
from typing import Optional

from models.portfolio_item import PortfolioItem
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class EADCalculator:
    """Calculate Exposure at Default (EAD) for credit exposures."""

    def __init__(self, config: Optional[dict] = None):
        """Initialize EAD calculator.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or get_config().get_section('ead')

    def calculate_current_ead(
        self,
        item: PortfolioItem,
        ccf_override: Optional[float] = None
    ) -> Decimal:
        """Calculate current EAD.

        EAD = Outstanding + (CCF × Undrawn)

        Args:
            item: Portfolio item
            ccf_override: Optional CCF override (otherwise uses config)

        Returns:
            Current EAD
        """
        # Get credit conversion factor
        ccf = self._get_ccf(item, ccf_override)

        # Calculate EAD
        undrawn_exposure = item.undrawn_commitment * Decimal(str(ccf))
        ead = item.outstanding_amount + undrawn_exposure

        logger.debug(
            "Calculated current EAD",
            item_id=item.item_id,
            outstanding=float(item.outstanding_amount),
            undrawn=float(item.undrawn_commitment),
            ccf=ccf,
            ead=float(ead)
        )

        return ead

    def project_ead(
        self,
        item: PortfolioItem,
        months_ahead: int,
        ccf_override: Optional[float] = None,
        prepayment_rate: float = 0.0,
        drawdown_rate: float = 0.0
    ) -> Decimal:
        """Project future EAD.

        Args:
            item: Portfolio item
            months_ahead: Number of months to project forward
            ccf_override: Optional CCF override
            prepayment_rate: Monthly prepayment rate (as decimal)
            drawdown_rate: Monthly drawdown rate of undrawn (as decimal)

        Returns:
            Projected EAD
        """
        # Start with current amounts
        outstanding = float(item.outstanding_amount)
        undrawn = float(item.undrawn_commitment)

        # Project forward month by month
        for _ in range(months_ahead):
            # Apply prepayments
            outstanding = outstanding * (1 - prepayment_rate)

            # Apply drawdowns
            drawdown = undrawn * drawdown_rate
            outstanding += drawdown
            undrawn -= drawdown

        # Get CCF
        ccf = self._get_ccf(item, ccf_override)

        # Calculate projected EAD
        ead = Decimal(str(outstanding)) + (Decimal(str(undrawn)) * Decimal(str(ccf)))

        return ead

    def _get_ccf(self, item: PortfolioItem, ccf_override: Optional[float] = None) -> float:
        """Get credit conversion factor for item.

        Args:
            item: Portfolio item
            ccf_override: Optional CCF override

        Returns:
            Credit conversion factor
        """
        if ccf_override is not None:
            return ccf_override

        # Try product-specific CCF
        ccf_by_product = self.config.get('ccf_by_product', {})
        product_type_lower = item.product_type.lower().replace(' ', '_')

        if product_type_lower in ccf_by_product:
            return ccf_by_product[product_type_lower]

        # Use default CCF
        return self.config.get('ccf', 0.75)

    def calculate_ead_with_scenario_adjustment(
        self,
        item: PortfolioItem,
        scenario_multiplier: float = 1.0
    ) -> Decimal:
        """Calculate EAD with scenario-specific adjustment.

        In stressed scenarios, undrawn commitments may be drawn more heavily.

        Args:
            item: Portfolio item
            scenario_multiplier: Multiplier for EAD (e.g., 1.2 in stress)

        Returns:
            Adjusted EAD
        """
        base_ead = self.calculate_current_ead(item)
        adjusted_ead = base_ead * Decimal(str(scenario_multiplier))

        logger.debug(
            "Applied scenario adjustment to EAD",
            item_id=item.item_id,
            base_ead=float(base_ead),
            multiplier=scenario_multiplier,
            adjusted_ead=float(adjusted_ead)
        )

        return adjusted_ead
