# IFRS 9 ECL Risk Modeling System

Advanced Expected Credit Loss (ECL) calculation system compliant with IFRS 9 accounting standards. Features full staging logic, multi-scenario analysis, stress testing, and comprehensive reporting.

## 🚀 Getting Started

### 🌐 View Sample Results in Browser (Instant!)

**See what the system produces - no installation needed:**

👉 **[Open Interactive ECL Report](ecl_report.html)** *(download and open in any browser)*

This sample report shows:
- Portfolio ECL summary: $113,983 total
- Multi-scenario analysis (5 economic scenarios)
- Stage breakdown (Stage 1/2/3)
- Sector distribution with interactive charts

### Run in Google Colab (No Installation Required!)

Click the badge below to open and run in Google Colab:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jennibhroin/riskmodelling-tool/blob/main/IFRS9_ECL_Colab.ipynb)

**Features in Colab:**
- ✅ No local installation needed
- ✅ Run ECL calculations in your browser
- ✅ Upload your own portfolio data
- ✅ Download results to Excel
- ✅ Interactive visualizations

### Clone and Run Locally

```bash
# Clone the repository
git clone https://github.com/jennibhroin/riskmodelling-tool.git
cd riskmodelling-tool

# Install dependencies
pip install -r requirements.txt

# Run example calculation
python examples/basic_ecl_calculation.py

# Run multi-scenario analysis
python examples/scenario_analysis.py
```

### Quick Test

```python
python3 << EOF
from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine

items = PortfolioLoader.load_from_csv('examples/sample_portfolio.csv')
engine = ECLCalculationEngine()
results = engine.calculate_portfolio_ecl(items)
print(f"Total ECL: \${results.total_ecl:,.2f}")
print(f"Coverage Ratio: {results.coverage_ratio:.2%}")
EOF
```

## Features

- **IFRS 9 Compliance**: Full staging framework (Stage 1/2/3) with SICR detection
- **Multi-Scenario Analysis**: Base, optimistic, pessimistic, and custom stress scenarios
- **Forward-Looking**: Macroeconomic variable integration for PD/LGD adjustments
- **Comprehensive Calculations**: PD × LGD × EAD with lifetime ECL for Stage 2/3
- **Stress Testing**: Pre-built recession and market shock scenarios
- **Portfolio Management**: Load from CSV/Excel, filter, aggregate
- **Rich Reporting**: Summary reports, stage migration analysis, visualizations
- **Flexible Configuration**: YAML-based configuration for all parameters
- **Production-Ready**: Extensive logging, error handling, and validation

### Use with Your Own Data

```python
from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine
from scenarios.scenario_manager import ScenarioManager

# Load your portfolio
items = PortfolioLoader.load_from_csv('your_portfolio.csv')

# Calculate ECL with multiple scenarios
scenario_mgr = ScenarioManager()
scenario_mgr.load_from_config('config/scenarios_config.yaml')

engine = ECLCalculationEngine()
results = {}
for scenario in scenario_mgr.list_scenarios():
    results[scenario.name] = engine.calculate_portfolio_ecl(items, scenario)

# Get probability-weighted ECL
weighted_ecl = scenario_mgr.calculate_weighted_ecl(results)
print(f"Probability-Weighted ECL: ${weighted_ecl:,.2f}")
```

## Installation

### From GitHub

```bash
git clone https://github.com/jennibhroin/riskmodelling-tool.git
cd riskmodelling-tool
pip install -r requirements.txt
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Load Portfolio

```python
from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine

# Load portfolio from CSV
items = PortfolioLoader.load_from_csv('examples/sample_portfolio.csv')

# Create ECL engine
engine = ECLCalculationEngine()

# Calculate ECL
results = engine.calculate_portfolio_ecl(items)

# Print summary
print(f"Total ECL: ${results.total_ecl:,.2f}")
print(f"Coverage Ratio: {results.coverage_ratio:.2%}")
print(f"Stage 2 Ratio: {results.stage_2_ratio:.2%}")
```

### 2. Multi-Scenario Analysis

```python
from scenarios.scenario_manager import ScenarioManager

# Load scenarios
scenario_mgr = ScenarioManager()
scenario_mgr.load_from_config('config/scenarios_config.yaml')

# Calculate ECL for each scenario
scenario_results = {}
for scenario in scenario_mgr.list_scenarios():
    result = engine.calculate_portfolio_ecl(items, scenario=scenario)
    scenario_results[scenario.name] = result

# Calculate probability-weighted ECL
weighted_ecl = scenario_mgr.calculate_weighted_ecl(scenario_results)
print(f"Probability-Weighted ECL: ${weighted_ecl:,.2f}")
```

### 3. Stress Testing

```python
from stress_testing.stress_scenarios import StressScenarioLibrary

# Load stress scenarios
stress_lib = StressScenarioLibrary()

# Run recession stress test
recession_scenario = stress_lib.get_scenario('recession')
stress_result = engine.calculate_portfolio_ecl(items, scenario=recession_scenario)

print(f"Base ECL: ${results.total_ecl:,.2f}")
print(f"Stress ECL: ${stress_result.total_ecl:,.2f}")
print(f"Increase: {(stress_result.total_ecl / results.total_ecl - 1):.1%}")
```

## Architecture

### Core Modules

- **core/ecl_engine.py**: Main ECL calculation orchestrator
- **core/probability_of_default.py**: PD calculations with lifetime curves
- **core/loss_given_default.py**: LGD with collateral adjustments
- **core/exposure.py**: EAD calculations with CCF
- **core/staging_framework.py**: IFRS 9 staging logic
- **core/portfolio.py**: Portfolio management and aggregation

### Data Management

- **data_management/portfolio_loader.py**: Import from CSV/Excel
- **data_management/validation.py**: Data quality checks
- **data_management/portfolio_exporter.py**: Export to CSV/Excel/JSON

### Scenario Framework

- **scenarios/scenario_manager.py**: Multi-scenario orchestration
- **scenarios/macroeconomic_model.py**: Macro variable modeling
- **scenarios/forward_looking.py**: PD/LGD adjustments

### Models

- **models/enums.py**: Stage, ScenarioType, CalculationMethod
- **models/portfolio_item.py**: Individual exposure data
- **models/calculation_results.py**: ECL results
- **models/scenario_config.py**: Scenario configuration

## Configuration

### Default Configuration (config/default_config.yaml)

```yaml
ecl:
  sicr_thresholds:
    pd_increase_bps: 30          # 30 bps absolute PD increase
    relative_increase_pct: 200   # 200% relative PD increase
    days_past_due: 30            # 30 DPD threshold

staging:
  days_past_due_threshold: 30    # Stage 2 threshold
  days_past_due_default: 90      # Stage 3 threshold
  cure_period: 3                 # Months for cure

lgd:
  unsecured_base: 0.45           # 45% LGD for unsecured
  secured_base: 0.25             # 25% LGD for secured
  downturn_multiplier: 1.25      # 25% downturn adjustment

ead:
  ccf: 0.75                      # Default CCF 75%
```

### Scenario Configuration (config/scenarios_config.yaml)

```yaml
scenarios:
  base:
    probability: 0.50
    pd_multiplier: 1.0
    lgd_multiplier: 1.0

  pessimistic:
    probability: 0.25
    macro_adjustments:
      gdp_growth: -2.0
      unemployment_rate: 2.0
    pd_multiplier: 1.30
    lgd_multiplier: 1.20
```

## Portfolio CSV Format

```csv
item_id,borrower_id,origination_date,maturity_date,outstanding_amount,undrawn_commitment,interest_rate,sector,collateral_value,credit_score,days_past_due,current_stage
LOAN001,BORR001,2020-01-15,2025-01-15,1000000,500000,5.5,Manufacturing,800000,720,0,Stage 1
LOAN002,BORR002,2019-06-01,2024-06-01,500000,0,6.2,Retail,300000,650,45,Stage 2
```

## IFRS 9 Staging Logic

### Stage 1: Performing (12-month ECL)
- No significant increase in credit risk (SICR)
- Days past due ≤ 30
- ECL = 12-month PD × LGD × EAD

### Stage 2: SICR Detected (Lifetime ECL)
- PD increase ≥ 30 bps OR
- Relative PD increase ≥ 200% OR
- Days past due > 30
- ECL = Lifetime PD × LGD × EAD

### Stage 3: Credit-Impaired (Lifetime ECL)
- Days past due > 90 OR
- Forbearance/restructuring OR
- Credit impairment indicators
- ECL = Lifetime PD × LGD × EAD (with downturn LGD)

## ECL Calculation Formula

```
ECL = PD × LGD × EAD

Where:
- PD = Probability of Default (12-month or lifetime)
- LGD = Loss Given Default (percentage of EAD)
- EAD = Exposure at Default (outstanding + CCF × undrawn)

Probability-Weighted ECL:
Total ECL = Σ(Scenario_ECLᵢ × Probabilityᵢ)
```

## Testing

### Run all tests

```bash
pytest tests/ -v --cov=. --cov-report=html
```

### Run unit tests only

```bash
pytest tests/unit/ -v
```

### Run with coverage

```bash
pytest --cov=core --cov=data_management --cov=models --cov-report=term-missing
```

## Examples

See the `examples/` directory for:
- `basic_ecl_calculation.py`: Simple ECL calculation
- `scenario_analysis.py`: Multi-scenario workflow
- `stress_testing.py`: Stress test demonstration
- `sample_portfolio.csv`: Sample input data

## API Reference

### ECLCalculationEngine

Main engine for ECL calculations.

```python
engine = ECLCalculationEngine()

# Single item ECL
result = engine.calculate_ecl(item, scenario=None)

# Portfolio ECL
portfolio_result = engine.calculate_portfolio_ecl(items, scenario=None)
```

### Portfolio

Portfolio management class.

```python
from core.portfolio import Portfolio

portfolio = Portfolio(items)

# Filter by stage
stage_2_items = portfolio.filter_by_stage(Stage.STAGE_2)

# Get statistics
summary = portfolio.get_summary()
```

### ScenarioManager

Multi-scenario analysis manager.

```python
from scenarios.scenario_manager import ScenarioManager

mgr = ScenarioManager()
mgr.load_from_config('config/scenarios_config.yaml')

# Calculate weighted ECL
weighted_ecl = mgr.calculate_weighted_ecl(scenario_results)
```

## Configuration Options

### PD Configuration

- `credit_score_min/max`: Credit score range (300-850)
- `floor`: Minimum PD (default: 0.0001 = 1 bp)
- `ceiling`: Maximum PD (default: 0.99 = 99%)
- `term_structure`: Monthly marginal default rates by stage

### LGD Configuration

- `unsecured_base`: Base LGD for unsecured exposures
- `secured_base`: Base LGD for secured exposures
- `collateral_haircuts`: Haircuts by collateral type
- `downturn_multiplier`: Downturn adjustment factor

### EAD Configuration

- `ccf`: Default credit conversion factor
- `ccf_by_product`: Product-specific CCFs

## Regulatory Compliance

- **IFRS 9 Standard**: Full compliance with staging requirements
- **SICR Detection**: Multiple criteria (DPD, PD changes, qualitative)
- **Forward-Looking**: Macroeconomic scenario integration
- **Multiple Scenarios**: Probability-weighted expected value
- **Audit Trail**: Comprehensive logging of calculations

## Performance

- Handles portfolios of 100,000+ exposures
- Vectorized calculations with NumPy
- Configurable parallel processing
- Efficient memory usage with Decimal precision

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/example/ifrs9-ecl-system/issues
- Documentation: https://github.com/example/ifrs9-ecl-system/wiki
- Email: risk@example.com

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Changelog

### Version 1.0.0 (2024-01-01)
- Initial release
- Full IFRS 9 staging framework
- Multi-scenario analysis
- Stress testing capabilities
- Comprehensive reporting
