"""Portfolio data loading from various sources."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any

import pandas as pd

from models.portfolio_item import PortfolioItem
from models.enums import Stage
from utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioLoader:
    """Load portfolio data from CSV, Excel, or other sources."""

    # Standard column mapping
    COLUMN_MAPPING = {
        'item_id': ['item_id', 'loan_id', 'id', 'exposure_id'],
        'borrower_id': ['borrower_id', 'client_id', 'customer_id'],
        'origination_date': ['origination_date', 'inception_date', 'start_date'],
        'maturity_date': ['maturity_date', 'end_date', 'expiry_date'],
        'reporting_date': ['reporting_date', 'as_of_date', 'valuation_date'],
        'outstanding_amount': ['outstanding_amount', 'outstanding', 'balance', 'exposure'],
        'undrawn_commitment': ['undrawn_commitment', 'undrawn', 'available_credit'],
        'interest_rate': ['interest_rate', 'rate', 'coupon'],
        'sector': ['sector', 'industry'],
        'product_type': ['product_type', 'product', 'loan_type'],
        'collateral_value': ['collateral_value', 'collateral', 'security_value'],
        'collateral_type': ['collateral_type', 'security_type'],
        'credit_score': ['credit_score', 'score', 'fico_score'],
        'internal_rating': ['internal_rating', 'rating', 'grade'],
        'external_rating': ['external_rating', 'external_grade'],
        'days_past_due': ['days_past_due', 'dpd', 'delinquency_days'],
        'times_past_due_12m': ['times_past_due_12m', 'times_past_due'],
        'is_forborne': ['is_forborne', 'forborne', 'forbearance'],
        'is_restructured': ['is_restructured', 'restructured'],
        'current_stage': ['current_stage', 'stage', 'ifrs9_stage'],
        'previous_stage': ['previous_stage', 'prior_stage'],
        'origination_pd': ['origination_pd', 'initial_pd'],
        'previous_pd': ['previous_pd', 'prior_pd'],
        'country': ['country', 'jurisdiction'],
        'region': ['region', 'geography'],
        'currency': ['currency', 'ccy'],
    }

    @classmethod
    def load_from_csv(
        cls,
        file_path: str,
        column_mapping: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> List[PortfolioItem]:
        """Load portfolio from CSV file.

        Args:
            file_path: Path to CSV file
            column_mapping: Custom column name mapping
            **kwargs: Additional arguments passed to pandas read_csv

        Returns:
            List of PortfolioItem objects
        """
        logger.info("Loading portfolio from CSV", file_path=file_path)

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read CSV
        df = pd.read_csv(file_path, **kwargs)
        logger.info("CSV loaded", rows=len(df), columns=list(df.columns))

        # Apply column mapping
        df = cls._apply_column_mapping(df, column_mapping)

        # Convert to PortfolioItem objects
        items = cls._dataframe_to_items(df)

        logger.info("Portfolio loaded successfully", item_count=len(items))
        return items

    @classmethod
    def load_from_excel(
        cls,
        file_path: str,
        sheet_name: str = 0,
        column_mapping: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> List[PortfolioItem]:
        """Load portfolio from Excel file.

        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name or index to load
            column_mapping: Custom column name mapping
            **kwargs: Additional arguments passed to pandas read_excel

        Returns:
            List of PortfolioItem objects
        """
        logger.info("Loading portfolio from Excel", file_path=file_path, sheet=sheet_name)

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read Excel
        df = pd.read_excel(file_path, sheet_name=sheet_name, **kwargs)
        logger.info("Excel loaded", rows=len(df), columns=list(df.columns))

        # Apply column mapping
        df = cls._apply_column_mapping(df, column_mapping)

        # Convert to PortfolioItem objects
        items = cls._dataframe_to_items(df)

        logger.info("Portfolio loaded successfully", item_count=len(items))
        return items

    @classmethod
    def load_from_dataframe(
        cls,
        df: pd.DataFrame,
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> List[PortfolioItem]:
        """Load portfolio from pandas DataFrame.

        Args:
            df: pandas DataFrame with portfolio data
            column_mapping: Custom column name mapping

        Returns:
            List of PortfolioItem objects
        """
        logger.info("Loading portfolio from DataFrame", rows=len(df))

        # Apply column mapping
        df = cls._apply_column_mapping(df, column_mapping)

        # Convert to PortfolioItem objects
        items = cls._dataframe_to_items(df)

        logger.info("Portfolio loaded successfully", item_count=len(items))
        return items

    @classmethod
    def _apply_column_mapping(
        cls,
        df: pd.DataFrame,
        custom_mapping: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """Apply column name mapping to standardize DataFrame.

        Args:
            df: Input DataFrame
            custom_mapping: Custom column mapping (overrides default)

        Returns:
            DataFrame with standardized column names
        """
        df = df.copy()

        # Build reverse mapping (file column -> standard column)
        reverse_mapping = {}
        for standard_col, possible_cols in cls.COLUMN_MAPPING.items():
            for col in possible_cols:
                if col in df.columns:
                    reverse_mapping[col] = standard_col
                    break

        # Apply custom mapping
        if custom_mapping:
            reverse_mapping.update(custom_mapping)

        # Rename columns
        df.rename(columns=reverse_mapping, inplace=True)

        return df

    @classmethod
    def _dataframe_to_items(cls, df: pd.DataFrame) -> List[PortfolioItem]:
        """Convert DataFrame to list of PortfolioItem objects.

        Args:
            df: DataFrame with standardized column names

        Returns:
            List of PortfolioItem objects
        """
        items = []

        for idx, row in df.iterrows():
            try:
                item_data = cls._row_to_dict(row)
                item = PortfolioItem(**item_data)
                items.append(item)
            except Exception as e:
                logger.warning(
                    "Failed to create PortfolioItem",
                    row_index=idx,
                    error=str(e)
                )
                # Continue processing other rows

        return items

    @classmethod
    def _row_to_dict(cls, row: pd.Series) -> Dict[str, Any]:
        """Convert DataFrame row to dictionary suitable for PortfolioItem.

        Args:
            row: DataFrame row

        Returns:
            Dictionary with PortfolioItem attributes
        """
        data = {}

        # Required fields
        data['item_id'] = str(row.get('item_id', ''))
        data['borrower_id'] = str(row.get('borrower_id', ''))

        # Dates
        data['origination_date'] = cls._parse_date(row.get('origination_date'))
        data['maturity_date'] = cls._parse_date(row.get('maturity_date'))
        if 'reporting_date' in row and pd.notna(row['reporting_date']):
            data['reporting_date'] = cls._parse_date(row['reporting_date'])

        # Amounts
        data['outstanding_amount'] = cls._parse_decimal(row.get('outstanding_amount', 0))

        # Optional numeric fields
        if 'undrawn_commitment' in row and pd.notna(row['undrawn_commitment']):
            data['undrawn_commitment'] = cls._parse_decimal(row['undrawn_commitment'])
        if 'interest_rate' in row and pd.notna(row['interest_rate']):
            data['interest_rate'] = float(row['interest_rate'])
        if 'collateral_value' in row and pd.notna(row['collateral_value']):
            data['collateral_value'] = cls._parse_decimal(row['collateral_value'])
        if 'credit_score' in row and pd.notna(row['credit_score']):
            data['credit_score'] = int(row['credit_score'])
        if 'days_past_due' in row and pd.notna(row['days_past_due']):
            data['days_past_due'] = int(row['days_past_due'])
        if 'times_past_due_12m' in row and pd.notna(row['times_past_due_12m']):
            data['times_past_due_12m'] = int(row['times_past_due_12m'])

        # Optional string fields
        for field in ['sector', 'product_type', 'currency', 'collateral_type',
                      'internal_rating', 'external_rating', 'country', 'region']:
            if field in row and pd.notna(row[field]):
                data[field] = str(row[field])

        # Boolean fields
        if 'is_forborne' in row and pd.notna(row['is_forborne']):
            data['is_forborne'] = bool(row['is_forborne'])
        if 'is_restructured' in row and pd.notna(row['is_restructured']):
            data['is_restructured'] = bool(row['is_restructured'])

        # Stage
        if 'current_stage' in row and pd.notna(row['current_stage']):
            data['current_stage'] = cls._parse_stage(row['current_stage'])
        if 'previous_stage' in row and pd.notna(row['previous_stage']):
            data['previous_stage'] = cls._parse_stage(row['previous_stage'])
        if 'origination_stage' in row and pd.notna(row['origination_stage']):
            data['origination_stage'] = cls._parse_stage(row['origination_stage'])

        # PD fields
        if 'origination_pd' in row and pd.notna(row['origination_pd']):
            data['origination_pd'] = float(row['origination_pd'])
        if 'previous_pd' in row and pd.notna(row['previous_pd']):
            data['previous_pd'] = float(row['previous_pd'])

        return data

    @staticmethod
    def _parse_date(value) -> date:
        """Parse date value from various formats.

        Args:
            value: Date value (string, datetime, or date)

        Returns:
            date object
        """
        if pd.isna(value):
            raise ValueError("Date value is required")

        if isinstance(value, date):
            return value
        if isinstance(value, pd.Timestamp):
            return value.date()
        if isinstance(value, str):
            return pd.to_datetime(value).date()

        raise ValueError(f"Cannot parse date from: {value}")

    @staticmethod
    def _parse_decimal(value) -> Decimal:
        """Parse decimal value.

        Args:
            value: Numeric value

        Returns:
            Decimal object
        """
        if pd.isna(value):
            return Decimal('0')
        return Decimal(str(value))

    @staticmethod
    def _parse_stage(value) -> Stage:
        """Parse stage value.

        Args:
            value: Stage value (string or Stage enum)

        Returns:
            Stage enum
        """
        if isinstance(value, Stage):
            return value

        value_str = str(value).strip()

        # Try direct enum value
        try:
            return Stage(value_str)
        except ValueError:
            pass

        # Try normalizing
        value_upper = value_str.upper()
        if 'STAGE 1' in value_upper or value_upper == '1':
            return Stage.STAGE_1
        elif 'STAGE 2' in value_upper or value_upper == '2':
            return Stage.STAGE_2
        elif 'STAGE 3' in value_upper or value_upper == '3':
            return Stage.STAGE_3

        raise ValueError(f"Cannot parse stage from: {value}")
