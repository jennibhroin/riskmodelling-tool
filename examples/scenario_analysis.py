"""Multi-scenario ECL analysis example."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine
from scenarios.scenario_manager import ScenarioManager


def main():
    """Run multi-scenario ECL analysis example."""
    print("=" * 80)
    print("IFRS 9 ECL Calculation - Multi-Scenario Analysis")
    print("=" * 80)
    print()

    # Load portfolio
    print("Loading portfolio from CSV...")
    csv_path = Path(__file__).parent / "sample_portfolio.csv"
    items = PortfolioLoader.load_from_csv(str(csv_path))
    print(f"Loaded {len(items)} portfolio items")
    print()

    # Initialize scenario manager
    print("Loading economic scenarios...")
    scenario_mgr = ScenarioManager()

    # Load scenarios from config
    config_path = Path(__file__).parent.parent / "config" / "scenarios_config.yaml"
    scenario_mgr.load_from_config(str(config_path))

    scenarios = scenario_mgr.list_scenarios()
    print(f"Loaded {len(scenarios)} scenarios:")
    for scenario in scenarios:
        print(f"  - {scenario.name:<20} ({str(scenario.scenario_type):<12}) "
              f"Probability: {scenario.probability:.1%}")
    print()

    # Validate probabilities
    print("Validating scenario probabilities...")
    if not scenario_mgr.validate_probabilities():
        print("  Warning: Probabilities do not sum to 1.0, normalizing...")
        scenario_mgr.normalize_probabilities()
    else:
        print("  ✓ Probabilities are valid")
    print()

    # Initialize ECL engine
    engine = ECLCalculationEngine()

    # Calculate ECL for each scenario
    print("Calculating ECL under each scenario...")
    print("-" * 80)
    scenario_results = {}

    for scenario in scenarios:
        result = engine.calculate_portfolio_ecl(items, scenario=scenario)
        scenario_results[scenario.name] = result

        print(f"\n{scenario.name.upper()} Scenario:")
        print(f"  Description:     {scenario.description}")
        print(f"  Probability:     {scenario.probability:.1%}")
        print(f"  Total ECL:       ${float(result.total_ecl):>15,.2f}")
        print(f"  Coverage Ratio:  {result.coverage_ratio:>15.2%}")
        print(f"  Stage 1 ECL:     ${float(result.stage_1_ecl):>15,.2f}")
        print(f"  Stage 2 ECL:     ${float(result.stage_2_ecl):>15,.2f}")
        print(f"  Stage 3 ECL:     ${float(result.stage_3_ecl):>15,.2f}")

    print()
    print("=" * 80)

    # Calculate probability-weighted ECL
    print("\nProbability-Weighted ECL:")
    print("-" * 80)

    weighted_ecl = scenario_mgr.calculate_weighted_ecl(scenario_results)
    weighted_result = scenario_mgr.calculate_weighted_portfolio_result(scenario_results)

    print(f"Weighted Total ECL:       ${float(weighted_ecl):>15,.2f}")
    print(f"Weighted Coverage Ratio:  {weighted_result.coverage_ratio:>15.2%}")
    print()

    print("Weighted ECL by Stage:")
    print(f"  Stage 1: ${float(weighted_result.stage_1_ecl):>15,.2f}")
    print(f"  Stage 2: ${float(weighted_result.stage_2_ecl):>15,.2f}")
    print(f"  Stage 3: ${float(weighted_result.stage_3_ecl):>15,.2f}")
    print()

    # Scenario comparison
    print("=" * 80)
    print("Scenario Comparison:")
    print("-" * 80)

    comparison = scenario_mgr.get_scenario_comparison(scenario_results)

    print(f"\n{'Scenario':<20} {'Probability':>12} {'Total ECL':>18} {'Coverage':>10}")
    print("-" * 80)

    for scenario_name in sorted(comparison['scenarios'].keys()):
        data = comparison['scenarios'][scenario_name]
        print(f"{scenario_name:<20} {data['probability']:>11.1%} "
              f"${data['total_ecl']:>16,.2f} {data['coverage_ratio']:>9.2%}")

    print("-" * 80)
    print(f"{'Weighted Average':<20} {' ':>12} ${comparison['weighted_ecl']:>16,.2f}")
    print()

    print(f"ECL Range: ${comparison['min_ecl']:,.2f} - ${comparison['max_ecl']:,.2f} "
          f"(Range: ${comparison['range_ecl']:,.2f})")
    print()

    # Macroeconomic changes
    print("=" * 80)
    print("Macroeconomic Scenario Details:")
    print("-" * 80)

    for scenario in scenarios[:3]:  # Show first 3 scenarios
        print(f"\n{scenario.name.upper()} Scenario:")
        macro_model = scenario_mgr.get_macro_model(scenario.name)
        if macro_model:
            changes = macro_model.get_changes_from_baseline()
            print(f"  GDP Growth:          {changes.get('gdp_growth', 0):>6.1f} pp")
            print(f"  Unemployment Rate:   {changes.get('unemployment_rate', 0):>6.1f} pp")
            print(f"  Interest Rate:       {changes.get('interest_rate', 0):>6.1f} pp")
            print(f"  Credit Spreads:      {changes.get('credit_spreads', 0):>6.0f} bps")
            print(f"  House Price Index:   {changes.get('house_price_index', 0):>6.1f}%")
            print(f"  Stock Market Index:  {changes.get('stock_market_index', 0):>6.1f}%")

    print()
    print("=" * 80)

    # Sensitivity analysis
    print("\nScenario Sensitivity Analysis:")
    print("-" * 80)

    base_ecl = float(scenario_results.get('base', scenario_results[list(scenario_results.keys())[0]]).total_ecl)

    print(f"\n{'Scenario':<20} {'ECL Change':>15} {'% Change':>12}")
    print("-" * 80)

    for scenario_name, result in scenario_results.items():
        ecl = float(result.total_ecl)
        change = ecl - base_ecl
        pct_change = (ecl / base_ecl - 1) * 100 if base_ecl > 0 else 0

        sign = "+" if change >= 0 else ""
        print(f"{scenario_name:<20} {sign}${change:>13,.2f} {sign}{pct_change:>10.1f}%")

    print()
    print("=" * 80)
    print("Multi-scenario analysis complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
