"""IFRS 9 staging framework for credit risk classification."""

from typing import List, Optional, Tuple, Dict
from collections import defaultdict

from models.portfolio_item import PortfolioItem
from models.enums import Stage
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


class StagingFramework:
    """IFRS 9 staging classification framework.

    Stage 1: Performing (12-month ECL)
    Stage 2: Significant increase in credit risk (lifetime ECL)
    Stage 3: Credit-impaired (lifetime ECL)
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize staging framework.

        Args:
            config: Optional configuration dictionary
        """
        staging_config = config or get_config().get_section('staging')
        ecl_config = get_config().get_section('ecl')

        self.dpd_stage_2_threshold = staging_config.get('days_past_due_threshold', 30)
        self.dpd_stage_3_threshold = staging_config.get('days_past_due_default', 90)
        self.cure_period = staging_config.get('cure_period', 3)

        # SICR thresholds
        sicr_config = ecl_config.get('sicr_thresholds', {})
        self.pd_increase_bps = sicr_config.get('pd_increase_bps', 30)
        self.relative_increase_pct = sicr_config.get('relative_increase_pct', 200)
        self.dpd_sicr_threshold = sicr_config.get('days_past_due', 30)

    def classify_stage(
        self,
        item: PortfolioItem,
        current_pd: Optional[float] = None
    ) -> Stage:
        """Classify portfolio item into IFRS 9 stage.

        Args:
            item: Portfolio item
            current_pd: Current PD (optional, for SICR detection)

        Returns:
            Stage classification
        """
        # Check Stage 3 criteria first (credit-impaired)
        if self.is_credit_impaired(item):
            logger.debug("Item classified as Stage 3", item_id=item.item_id)
            return Stage.STAGE_3

        # Check Stage 2 criteria (SICR)
        if self.detect_significant_increase_in_credit_risk(item, current_pd):
            logger.debug("Item classified as Stage 2", item_id=item.item_id)
            return Stage.STAGE_2

        # Default to Stage 1 (performing)
        logger.debug("Item classified as Stage 1", item_id=item.item_id)
        return Stage.STAGE_1

    def is_credit_impaired(self, item: PortfolioItem) -> bool:
        """Check if item meets Stage 3 (credit-impaired) criteria.

        Stage 3 criteria:
        - Days past due > 90
        - Forbearance or restructuring
        - Any other credit impairment indicator

        Args:
            item: Portfolio item

        Returns:
            True if credit-impaired
        """
        # DPD-based impairment
        if item.days_past_due > self.dpd_stage_3_threshold:
            logger.debug(
                "Credit impairment: DPD > threshold",
                item_id=item.item_id,
                dpd=item.days_past_due,
                threshold=self.dpd_stage_3_threshold
            )
            return True

        # Forbearance/restructuring (if significant)
        if item.is_forborne and item.days_past_due > 0:
            logger.debug(
                "Credit impairment: Forborne with DPD",
                item_id=item.item_id
            )
            return True

        if item.is_restructured and item.days_past_due > self.dpd_stage_2_threshold:
            logger.debug(
                "Credit impairment: Restructured with significant DPD",
                item_id=item.item_id
            )
            return True

        return False

    def detect_significant_increase_in_credit_risk(
        self,
        item: PortfolioItem,
        current_pd: Optional[float] = None
    ) -> bool:
        """Detect significant increase in credit risk (SICR) for Stage 2.

        SICR indicators:
        1. Absolute PD increase ≥ 30 bps from origination
        2. Relative PD increase ≥ 200% from origination
        3. Days past due > 30
        4. Multiple past due events in last 12 months

        Args:
            item: Portfolio item
            current_pd: Current PD (if available)

        Returns:
            True if SICR detected
        """
        # Days past due check
        if item.days_past_due > self.dpd_sicr_threshold:
            logger.debug(
                "SICR detected: DPD > threshold",
                item_id=item.item_id,
                dpd=item.days_past_due,
                threshold=self.dpd_sicr_threshold
            )
            return True

        # Multiple past due events
        if item.times_past_due_12m >= 2:
            logger.debug(
                "SICR detected: Multiple past due events",
                item_id=item.item_id,
                times_past_due=item.times_past_due_12m
            )
            return True

        # PD-based SICR detection (if PD data available)
        if current_pd is not None and item.origination_pd is not None:
            sicr_detected = self._check_pd_based_sicr(
                current_pd,
                item.origination_pd,
                item.item_id
            )
            if sicr_detected:
                return True

        # Forbearance indicator
        if item.is_forborne or item.is_restructured:
            logger.debug(
                "SICR detected: Forbearance or restructuring",
                item_id=item.item_id
            )
            return True

        return False

    def _check_pd_based_sicr(
        self,
        current_pd: float,
        origination_pd: float,
        item_id: str
    ) -> bool:
        """Check for SICR based on PD changes.

        Args:
            current_pd: Current PD
            origination_pd: PD at origination
            item_id: Item ID for logging

        Returns:
            True if SICR detected based on PD
        """
        # Absolute PD increase in basis points
        pd_increase_bps = (current_pd - origination_pd) * 10000

        if pd_increase_bps >= self.pd_increase_bps:
            logger.debug(
                "SICR detected: Absolute PD increase",
                item_id=item_id,
                current_pd=current_pd,
                origination_pd=origination_pd,
                increase_bps=pd_increase_bps,
                threshold_bps=self.pd_increase_bps
            )
            return True

        # Relative PD increase as percentage
        if origination_pd > 0:
            relative_increase_pct = ((current_pd / origination_pd) - 1) * 100

            if relative_increase_pct >= self.relative_increase_pct:
                logger.debug(
                    "SICR detected: Relative PD increase",
                    item_id=item_id,
                    current_pd=current_pd,
                    origination_pd=origination_pd,
                    increase_pct=relative_increase_pct,
                    threshold_pct=self.relative_increase_pct
                )
                return True

        return False

    def perform_stage_migration(
        self,
        items: List[PortfolioItem],
        pd_calculator=None
    ) -> Tuple[List[PortfolioItem], Dict[str, int]]:
        """Perform stage migration for entire portfolio.

        Args:
            items: List of portfolio items
            pd_calculator: Optional PD calculator for SICR detection

        Returns:
            Tuple of (updated items, migration statistics)
        """
        migration_stats = defaultdict(int)
        updated_items = []

        for item in items:
            # Store previous stage
            previous_stage = item.current_stage

            # Calculate current PD if calculator provided
            current_pd = None
            if pd_calculator is not None:
                current_pd = pd_calculator.calculate_12m_pd(item)

            # Classify stage
            new_stage = self.classify_stage(item, current_pd)

            # Update item
            item.previous_stage = previous_stage
            item.current_stage = new_stage

            # Track migration
            migration_key = f"{previous_stage}_to_{new_stage}"
            migration_stats[migration_key] += 1

            if previous_stage != new_stage:
                logger.info(
                    "Stage migration",
                    item_id=item.item_id,
                    from_stage=str(previous_stage),
                    to_stage=str(new_stage)
                )

            updated_items.append(item)

        # Log summary
        total_migrations = sum(
            count for key, count in migration_stats.items()
            if '_to_' in key and key.split('_to_')[0] != key.split('_to_')[1]
        )

        logger.info(
            "Stage migration complete",
            total_items=len(items),
            total_migrations=total_migrations,
            stats=dict(migration_stats)
        )

        return updated_items, dict(migration_stats)

    def check_cure_eligibility(
        self,
        item: PortfolioItem,
        months_in_good_standing: int
    ) -> bool:
        """Check if item is eligible to move back to Stage 1 (cure).

        Args:
            item: Portfolio item
            months_in_good_standing: Months in good standing

        Returns:
            True if eligible for cure
        """
        # Must be in Stage 2 (Stage 3 requires more stringent cure criteria)
        if item.current_stage != Stage.STAGE_2:
            return False

        # Must have been in good standing for cure period
        if months_in_good_standing < self.cure_period:
            return False

        # No current delinquency
        if item.days_past_due > 0:
            return False

        # No recent past due events
        if item.times_past_due_12m > 0:
            return False

        return True

    def get_stage_summary(self, items: List[PortfolioItem]) -> Dict:
        """Get summary statistics by stage.

        Args:
            items: List of portfolio items

        Returns:
            Dictionary with stage statistics
        """
        from decimal import Decimal

        stage_counts = defaultdict(int)
        stage_exposure = defaultdict(Decimal)

        for item in items:
            stage_counts[item.current_stage] += 1
            stage_exposure[item.current_stage] += item.total_exposure

        total_exposure = sum(stage_exposure.values())

        summary = {
            'stage_1': {
                'count': stage_counts[Stage.STAGE_1],
                'exposure': float(stage_exposure[Stage.STAGE_1]),
                'exposure_pct': float(stage_exposure[Stage.STAGE_1] / total_exposure * 100) if total_exposure > 0 else 0,
            },
            'stage_2': {
                'count': stage_counts[Stage.STAGE_2],
                'exposure': float(stage_exposure[Stage.STAGE_2]),
                'exposure_pct': float(stage_exposure[Stage.STAGE_2] / total_exposure * 100) if total_exposure > 0 else 0,
            },
            'stage_3': {
                'count': stage_counts[Stage.STAGE_3],
                'exposure': float(stage_exposure[Stage.STAGE_3]),
                'exposure_pct': float(stage_exposure[Stage.STAGE_3] / total_exposure * 100) if total_exposure > 0 else 0,
            },
            'total': {
                'count': len(items),
                'exposure': float(total_exposure),
            }
        }

        return summary
