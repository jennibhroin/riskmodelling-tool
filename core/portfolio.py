"""Portfolio management and aggregation."""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Callable
from collections import defaultdict

from models.portfolio_item import PortfolioItem
from models.enums import Stage
from utils.logger import get_logger

logger = get_logger(__name__)


class Portfolio:
    """Manages a collection of portfolio items with filtering and aggregation."""

    def __init__(self, items: Optional[List[PortfolioItem]] = None):
        """Initialize portfolio.

        Args:
            items: Initial list of portfolio items
        """
        self._items: List[PortfolioItem] = items or []
        self._index: Dict[str, PortfolioItem] = {}
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild item ID index."""
        self._index = {item.item_id: item for item in self._items}

    def add(self, item: PortfolioItem):
        """Add item to portfolio.

        Args:
            item: Portfolio item to add
        """
        if item.item_id in self._index:
            logger.warning("Replacing existing item", item_id=item.item_id)
            self.remove(item.item_id)

        self._items.append(item)
        self._index[item.item_id] = item

    def add_many(self, items: List[PortfolioItem]):
        """Add multiple items to portfolio.

        Args:
            items: List of portfolio items to add
        """
        for item in items:
            self.add(item)

    def remove(self, item_id: str) -> bool:
        """Remove item from portfolio.

        Args:
            item_id: ID of item to remove

        Returns:
            True if item was removed, False if not found
        """
        if item_id not in self._index:
            return False

        item = self._index[item_id]
        self._items.remove(item)
        del self._index[item_id]
        return True

    def get(self, item_id: str) -> Optional[PortfolioItem]:
        """Get item by ID.

        Args:
            item_id: Item ID

        Returns:
            PortfolioItem or None if not found
        """
        return self._index.get(item_id)

    def filter(self, condition: Callable[[PortfolioItem], bool]) -> 'Portfolio':
        """Filter portfolio by condition.

        Args:
            condition: Function that returns True for items to keep

        Returns:
            New Portfolio with filtered items
        """
        filtered_items = [item for item in self._items if condition(item)]
        return Portfolio(filtered_items)

    def filter_by_stage(self, stage: Stage) -> 'Portfolio':
        """Filter portfolio by stage.

        Args:
            stage: Stage to filter by

        Returns:
            New Portfolio with items in specified stage
        """
        return self.filter(lambda item: item.current_stage == stage)

    def filter_by_sector(self, sector: str) -> 'Portfolio':
        """Filter portfolio by sector.

        Args:
            sector: Sector to filter by

        Returns:
            New Portfolio with items in specified sector
        """
        return self.filter(lambda item: item.sector == sector)

    def filter_by_product(self, product_type: str) -> 'Portfolio':
        """Filter portfolio by product type.

        Args:
            product_type: Product type to filter by

        Returns:
            New Portfolio with items of specified product type
        """
        return self.filter(lambda item: item.product_type == product_type)

    def filter_by_rating(self, internal_rating: str) -> 'Portfolio':
        """Filter portfolio by internal rating.

        Args:
            internal_rating: Internal rating to filter by

        Returns:
            New Portfolio with items of specified rating
        """
        return self.filter(lambda item: item.internal_rating == internal_rating)

    def items(self) -> List[PortfolioItem]:
        """Get all items in portfolio.

        Returns:
            List of all portfolio items
        """
        return self._items.copy()

    def __len__(self) -> int:
        """Get number of items in portfolio."""
        return len(self._items)

    def __iter__(self):
        """Iterate over portfolio items."""
        return iter(self._items)

    def __getitem__(self, item_id: str) -> PortfolioItem:
        """Get item by ID using bracket notation."""
        item = self.get(item_id)
        if item is None:
            raise KeyError(f"Item not found: {item_id}")
        return item

    # Summary statistics

    def total_exposure(self) -> Decimal:
        """Calculate total exposure (outstanding + undrawn)."""
        return sum(item.total_exposure for item in self._items)

    def total_outstanding(self) -> Decimal:
        """Calculate total outstanding amount."""
        return sum(item.outstanding_amount for item in self._items)

    def total_undrawn(self) -> Decimal:
        """Calculate total undrawn commitments."""
        return sum(item.undrawn_commitment for item in self._items)

    def total_collateral(self) -> Decimal:
        """Calculate total collateral value."""
        return sum(item.collateral_value for item in self._items)

    def average_credit_score(self) -> float:
        """Calculate average credit score."""
        if not self._items:
            return 0.0
        return sum(item.credit_score for item in self._items) / len(self._items)

    def average_ltv(self) -> float:
        """Calculate average loan-to-value ratio (excluding infinite values)."""
        if not self._items:
            return 0.0

        ltvs = [item.loan_to_value for item in self._items if item.loan_to_value != float('inf')]
        if not ltvs:
            return 0.0

        return sum(ltvs) / len(ltvs)

    def stage_distribution(self) -> Dict[Stage, int]:
        """Get distribution of items by stage.

        Returns:
            Dictionary mapping Stage to count
        """
        distribution = defaultdict(int)
        for item in self._items:
            distribution[item.current_stage] += 1
        return dict(distribution)

    def stage_exposure(self) -> Dict[Stage, Decimal]:
        """Get exposure by stage.

        Returns:
            Dictionary mapping Stage to total exposure
        """
        exposure = defaultdict(Decimal)
        for item in self._items:
            exposure[item.current_stage] += item.total_exposure
        return dict(exposure)

    def sector_distribution(self) -> Dict[str, int]:
        """Get distribution of items by sector.

        Returns:
            Dictionary mapping sector to count
        """
        distribution = defaultdict(int)
        for item in self._items:
            distribution[item.sector] += 1
        return dict(distribution)

    def sector_exposure(self) -> Dict[str, Decimal]:
        """Get exposure by sector.

        Returns:
            Dictionary mapping sector to total exposure
        """
        exposure = defaultdict(Decimal)
        for item in self._items:
            exposure[item.sector] += item.total_exposure
        return dict(exposure)

    def product_distribution(self) -> Dict[str, int]:
        """Get distribution of items by product type.

        Returns:
            Dictionary mapping product type to count
        """
        distribution = defaultdict(int)
        for item in self._items:
            distribution[item.product_type] += 1
        return dict(distribution)

    def product_exposure(self) -> Dict[str, Decimal]:
        """Get exposure by product type.

        Returns:
            Dictionary mapping product type to total exposure
        """
        exposure = defaultdict(Decimal)
        for item in self._items:
            exposure[item.product_type] += item.total_exposure
        return dict(exposure)

    def past_due_count(self) -> int:
        """Count items with any days past due."""
        return sum(1 for item in self._items if item.is_past_due)

    def defaulted_count(self) -> int:
        """Count defaulted items."""
        return sum(1 for item in self._items if item.is_defaulted)

    def get_summary(self) -> Dict:
        """Get comprehensive portfolio summary.

        Returns:
            Dictionary with portfolio statistics
        """
        stage_dist = self.stage_distribution()
        stage_exp = self.stage_exposure()

        return {
            'total_items': len(self._items),
            'total_exposure': float(self.total_exposure()),
            'total_outstanding': float(self.total_outstanding()),
            'total_undrawn': float(self.total_undrawn()),
            'total_collateral': float(self.total_collateral()),
            'average_credit_score': self.average_credit_score(),
            'average_ltv': self.average_ltv(),
            'past_due_count': self.past_due_count(),
            'defaulted_count': self.defaulted_count(),
            'stage_distribution': {
                str(stage): count for stage, count in stage_dist.items()
            },
            'stage_exposure': {
                str(stage): float(exp) for stage, exp in stage_exp.items()
            },
            'stage_1_ratio': float(stage_exp.get(Stage.STAGE_1, Decimal('0')) / self.total_exposure()) if self.total_exposure() > 0 else 0,
            'stage_2_ratio': float(stage_exp.get(Stage.STAGE_2, Decimal('0')) / self.total_exposure()) if self.total_exposure() > 0 else 0,
            'stage_3_ratio': float(stage_exp.get(Stage.STAGE_3, Decimal('0')) / self.total_exposure()) if self.total_exposure() > 0 else 0,
        }
