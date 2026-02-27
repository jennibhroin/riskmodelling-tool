"""Portfolio data export to various formats."""

import json
from pathlib import Path
from typing import List, Optional

import pandas as pd

from models.portfolio_item import PortfolioItem
from models.calculation_results import ECLResult, PortfolioECLResult
from utils.logger import get_logger

logger = get_logger(__name__)


class PortfolioExporter:
    """Export portfolio and ECL results to various formats."""

    @staticmethod
    def export_portfolio_to_csv(
        items: List[PortfolioItem],
        file_path: str
    ):
        """Export portfolio to CSV file.

        Args:
            items: List of portfolio items
            file_path: Output CSV file path
        """
        logger.info("Exporting portfolio to CSV", file_path=file_path, item_count=len(items))

        # Convert items to dictionaries
        data = [item.to_dict() for item in items]

        # Create DataFrame
        df = pd.DataFrame(data)

        # Save to CSV
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)

        logger.info("Portfolio exported to CSV", file_path=file_path)

    @staticmethod
    def export_portfolio_to_excel(
        items: List[PortfolioItem],
        file_path: str,
        sheet_name: str = "Portfolio"
    ):
        """Export portfolio to Excel file.

        Args:
            items: List of portfolio items
            file_path: Output Excel file path
            sheet_name: Sheet name in Excel file
        """
        logger.info("Exporting portfolio to Excel", file_path=file_path, item_count=len(items))

        # Convert items to dictionaries
        data = [item.to_dict() for item in items]

        # Create DataFrame
        df = pd.DataFrame(data)

        # Save to Excel
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, sheet_name=sheet_name, index=False)

        logger.info("Portfolio exported to Excel", file_path=file_path)

    @staticmethod
    def export_portfolio_to_json(
        items: List[PortfolioItem],
        file_path: str,
        indent: int = 2
    ):
        """Export portfolio to JSON file.

        Args:
            items: List of portfolio items
            file_path: Output JSON file path
            indent: JSON indentation
        """
        logger.info("Exporting portfolio to JSON", file_path=file_path, item_count=len(items))

        # Convert items to dictionaries
        data = [item.to_dict() for item in items]

        # Save to JSON
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(data, f, indent=indent, default=str)

        logger.info("Portfolio exported to JSON", file_path=file_path)

    @staticmethod
    def export_ecl_results_to_csv(
        results: List[ECLResult],
        file_path: str
    ):
        """Export ECL results to CSV file.

        Args:
            results: List of ECL results
            file_path: Output CSV file path
        """
        logger.info("Exporting ECL results to CSV", file_path=file_path, result_count=len(results))

        # Convert results to dictionaries
        data = [result.to_dict() for result in results]

        # Create DataFrame
        df = pd.DataFrame(data)

        # Save to CSV
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)

        logger.info("ECL results exported to CSV", file_path=file_path)

    @staticmethod
    def export_ecl_results_to_excel(
        results: List[ECLResult],
        file_path: str,
        sheet_name: str = "ECL Results"
    ):
        """Export ECL results to Excel file.

        Args:
            results: List of ECL results
            file_path: Output Excel file path
            sheet_name: Sheet name in Excel file
        """
        logger.info("Exporting ECL results to Excel", file_path=file_path, result_count=len(results))

        # Convert results to dictionaries
        data = [result.to_dict() for result in results]

        # Create DataFrame
        df = pd.DataFrame(data)

        # Save to Excel
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, sheet_name=sheet_name, index=False)

        logger.info("ECL results exported to Excel", file_path=file_path)

    @staticmethod
    def export_portfolio_ecl_to_excel(
        portfolio_result: PortfolioECLResult,
        file_path: str
    ):
        """Export portfolio ECL results to Excel with multiple sheets.

        Args:
            portfolio_result: Portfolio ECL result
            file_path: Output Excel file path
        """
        logger.info("Exporting portfolio ECL to Excel", file_path=file_path)

        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
            # Summary sheet
            summary = portfolio_result.get_summary()
            summary_df = pd.DataFrame([summary])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # Stage breakdown
            stage_data = [
                {
                    'Stage': 'Stage 1',
                    'ECL': float(portfolio_result.stage_1_ecl),
                    'Exposure': float(portfolio_result.stage_1_exposure),
                    'Count': portfolio_result.stage_1_count,
                    'Coverage': portfolio_result.stage_1_coverage,
                },
                {
                    'Stage': 'Stage 2',
                    'ECL': float(portfolio_result.stage_2_ecl),
                    'Exposure': float(portfolio_result.stage_2_exposure),
                    'Count': portfolio_result.stage_2_count,
                    'Coverage': portfolio_result.stage_2_coverage,
                },
                {
                    'Stage': 'Stage 3',
                    'ECL': float(portfolio_result.stage_3_ecl),
                    'Exposure': float(portfolio_result.stage_3_exposure),
                    'Count': portfolio_result.stage_3_count,
                    'Coverage': portfolio_result.stage_3_coverage,
                },
            ]
            stage_df = pd.DataFrame(stage_data)
            stage_df.to_excel(writer, sheet_name='Stage Breakdown', index=False)

            # Sector breakdown
            if portfolio_result.ecl_by_sector:
                sector_data = [
                    {'Sector': sector, 'ECL': float(ecl)}
                    for sector, ecl in portfolio_result.ecl_by_sector.items()
                ]
                sector_df = pd.DataFrame(sector_data)
                sector_df.to_excel(writer, sheet_name='By Sector', index=False)

            # Product breakdown
            if portfolio_result.ecl_by_product:
                product_data = [
                    {'Product': product, 'ECL': float(ecl)}
                    for product, ecl in portfolio_result.ecl_by_product.items()
                ]
                product_df = pd.DataFrame(product_data)
                product_df.to_excel(writer, sheet_name='By Product', index=False)

            # Individual results
            if portfolio_result.item_results:
                results_data = [result.to_dict() for result in portfolio_result.item_results]
                results_df = pd.DataFrame(results_data)
                results_df.to_excel(writer, sheet_name='Detailed Results', index=False)

        logger.info("Portfolio ECL exported to Excel", file_path=file_path)

    @staticmethod
    def export_ecl_results_to_json(
        results: List[ECLResult],
        file_path: str,
        indent: int = 2
    ):
        """Export ECL results to JSON file.

        Args:
            results: List of ECL results
            file_path: Output JSON file path
            indent: JSON indentation
        """
        logger.info("Exporting ECL results to JSON", file_path=file_path, result_count=len(results))

        # Convert results to dictionaries
        data = [result.to_dict() for result in results]

        # Save to JSON
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(data, f, indent=indent, default=str)

        logger.info("ECL results exported to JSON", file_path=file_path)

    @staticmethod
    def export_portfolio_ecl_to_json(
        portfolio_result: PortfolioECLResult,
        file_path: str,
        indent: int = 2
    ):
        """Export portfolio ECL result to JSON file.

        Args:
            portfolio_result: Portfolio ECL result
            file_path: Output JSON file path
            indent: JSON indentation
        """
        logger.info("Exporting portfolio ECL to JSON", file_path=file_path)

        # Convert to dictionary
        data = portfolio_result.to_dict()

        # Add detailed results
        if portfolio_result.item_results:
            data['detailed_results'] = [
                result.to_dict() for result in portfolio_result.item_results
            ]

        # Save to JSON
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            json.dump(data, f, indent=indent, default=str)

        logger.info("Portfolio ECL exported to JSON", file_path=file_path)
