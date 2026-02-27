"""Basic ECL calculation example."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine
from core.portfolio import Portfolio


def main():
    """Run basic ECL calculation example."""
    print("=" * 80)
    print("IFRS 9 ECL Calculation - Basic Example")
    print("=" * 80)
    print()

    # Load portfolio
    print("Loading portfolio from CSV...")
    csv_path = Path(__file__).parent / "sample_portfolio.csv"
    items = PortfolioLoader.load_from_csv(str(csv_path))
    print(f"Loaded {len(items)} portfolio items")
    print()

    # Create portfolio object
    portfolio = Portfolio(items)

    # Print portfolio summary
    print("Portfolio Summary:")
    print("-" * 80)
    summary = portfolio.get_summary()
    print(f"Total Items:      {summary['total_items']:,}")
    print(f"Total Exposure:   ${summary['total_exposure']:,.2f}")
    print(f"Avg Credit Score: {summary['average_credit_score']:.0f}")
    print()

    print("Stage Distribution:")
    for stage, count in summary['stage_distribution'].items():
        exposure = summary['stage_exposure'][stage]
        pct = (exposure / summary['total_exposure'] * 100) if summary['total_exposure'] > 0 else 0
        print(f"  {stage}: {count:2d} items, ${exposure:>15,.2f} ({pct:5.1f}%)")
    print()

    # Calculate ECL
    print("Calculating ECL...")
    engine = ECLCalculationEngine()
    results = engine.calculate_portfolio_ecl(items)
    print()

    # Print ECL results
    print("ECL Results:")
    print("=" * 80)
    print(f"Total ECL:          ${results.total_ecl:>15,.2f}")
    print(f"Total Exposure:     ${results.total_exposure:>15,.2f}")
    print(f"Coverage Ratio:     {results.coverage_ratio:>15.2%}")
    print()

    print("ECL by Stage:")
    print("-" * 80)
    print(f"{'Stage':<10} {'Count':>6} {'Exposure':>18} {'ECL':>18} {'Coverage':>10}")
    print("-" * 80)

    stages = [
        ('Stage 1', results.stage_1_count, results.stage_1_exposure,
         results.stage_1_ecl, results.stage_1_coverage),
        ('Stage 2', results.stage_2_count, results.stage_2_exposure,
         results.stage_2_ecl, results.stage_2_coverage),
        ('Stage 3', results.stage_3_count, results.stage_3_exposure,
         results.stage_3_ecl, results.stage_3_coverage),
    ]

    for stage_name, count, exposure, ecl, coverage in stages:
        print(f"{stage_name:<10} {count:>6,} ${float(exposure):>16,.2f} "
              f"${float(ecl):>16,.2f} {coverage:>9.2%}")

    print("-" * 80)
    print(f"{'Total':<10} {results.total_items:>6,} "
          f"${float(results.total_exposure):>16,.2f} "
          f"${float(results.total_ecl):>16,.2f} {results.coverage_ratio:>9.2%}")
    print()

    # ECL by sector
    print("ECL by Sector:")
    print("-" * 80)
    sector_totals = sorted(
        results.ecl_by_sector.items(),
        key=lambda x: x[1],
        reverse=True
    )
    for sector, ecl in sector_totals[:10]:  # Top 10 sectors
        pct = (float(ecl) / float(results.total_ecl) * 100) if results.total_ecl > 0 else 0
        print(f"  {sector:<25} ${float(ecl):>12,.2f} ({pct:5.1f}%)")
    print()

    # Sample individual results
    print("Sample Individual ECL Results (First 5 Items):")
    print("-" * 80)
    print(f"{'Item ID':<10} {'Stage':<10} {'PD':>8} {'LGD':>8} {'EAD':>15} {'ECL':>15}")
    print("-" * 80)

    for result in results.item_results[:5]:
        print(f"{result.item_id:<10} {str(result.stage):<10} "
              f"{result.probability_of_default:>7.2%} {result.loss_given_default:>7.2%} "
              f"${float(result.exposure_at_default):>13,.0f} "
              f"${float(result.ecl_amount):>13,.2f}")
    print()

    print("=" * 80)
    print("Calculation complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
