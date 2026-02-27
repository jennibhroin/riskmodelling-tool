# Quick Start Guide

Get up and running with the IFRS 9 ECL Risk Modeling System in 5 minutes.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/jennibhroin/riskmodelling-tool.git
cd riskmodelling-tool
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including pandas, numpy, pyyaml, and testing tools.

### 3. Run Your First ECL Calculation

**Option A: Run the example script**

```bash
python examples/basic_ecl_calculation.py
```

You should see output like:
```
Total ECL:          $113,983.39
Total Exposure:     $29,210,000.00
Coverage Ratio:     0.39%
```

**Option B: Run multi-scenario analysis**

```bash
python examples/scenario_analysis.py
```

This shows ECL under multiple economic scenarios.

### 4. Use the Python API

Create a new file `my_ecl_analysis.py`:

```python
from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine

# Load sample portfolio
items = PortfolioLoader.load_from_csv('examples/sample_portfolio.csv')

# Calculate ECL
engine = ECLCalculationEngine()
results = engine.calculate_portfolio_ecl(items)

# Display results
print(f"Total ECL: ${float(results.total_ecl):,.2f}")
print(f"Total Exposure: ${float(results.total_exposure):,.2f}")
print(f"Coverage Ratio: {results.coverage_ratio:.2%}")

print("\nECL by Stage:")
print(f"  Stage 1: ${float(results.stage_1_ecl):,.2f}")
print(f"  Stage 2: ${float(results.stage_2_ecl):,.2f}")
print(f"  Stage 3: ${float(results.stage_3_ecl):,.2f}")
```

Run it:
```bash
python my_ecl_analysis.py
```

## Using Your Own Data

### Portfolio CSV Format

Create a CSV file with your portfolio data:

```csv
item_id,borrower_id,origination_date,maturity_date,outstanding_amount,undrawn_commitment,interest_rate,sector,collateral_value,credit_score,days_past_due,current_stage
LOAN001,BORR001,2020-01-15,2025-01-15,1000000,500000,5.5,Manufacturing,800000,720,0,Stage 1
LOAN002,BORR002,2019-06-01,2024-06-01,500000,0,6.2,Retail,300000,650,45,Stage 2
```

**Required fields:**
- `item_id`: Unique loan identifier
- `borrower_id`: Borrower identifier
- `origination_date`: Loan start date (YYYY-MM-DD)
- `maturity_date`: Loan maturity date (YYYY-MM-DD)
- `outstanding_amount`: Current outstanding balance

**Optional but recommended:**
- `undrawn_commitment`: Available credit line
- `credit_score`: Credit score (300-850)
- `collateral_value`: Collateral value
- `days_past_due`: Days past due
- `current_stage`: Current IFRS 9 stage

### Calculate ECL for Your Portfolio

```python
from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine

# Load your portfolio
items = PortfolioLoader.load_from_csv('my_portfolio.csv')

# Calculate ECL
engine = ECLCalculationEngine()
results = engine.calculate_portfolio_ecl(items)

print(f"Total ECL: ${float(results.total_ecl):,.2f}")
```

## Multi-Scenario Analysis

Run ECL under multiple economic scenarios:

```python
from data_management.portfolio_loader import PortfolioLoader
from core.ecl_engine import ECLCalculationEngine
from scenarios.scenario_manager import ScenarioManager

# Load portfolio
items = PortfolioLoader.load_from_csv('my_portfolio.csv')

# Setup scenarios
scenario_mgr = ScenarioManager()
scenario_mgr.load_from_config('config/scenarios_config.yaml')

# Calculate ECL for each scenario
engine = ECLCalculationEngine()
scenario_results = {}

for scenario in scenario_mgr.list_scenarios():
    result = engine.calculate_portfolio_ecl(items, scenario=scenario)
    scenario_results[scenario.name] = result
    print(f"{scenario.name}: ${float(result.total_ecl):,.2f}")

# Get probability-weighted ECL
weighted_ecl = scenario_mgr.calculate_weighted_ecl(scenario_results)
print(f"\nProbability-Weighted ECL: ${float(weighted_ecl):,.2f}")
```

## Export Results

Export results to Excel:

```python
from data_management.portfolio_exporter import PortfolioExporter

# Export portfolio ECL results
PortfolioExporter.export_portfolio_ecl_to_excel(
    results,
    'ecl_results.xlsx'
)
```

## Running Tests

Verify everything is working:

```bash
# Run all tests
python -m pytest tests/ -v

# Run unit tests only
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v
```

## Common Issues

### ImportError: No module named 'pandas'

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### FileNotFoundError: portfolio.csv not found

**Solution:** Use absolute path or ensure working directory is correct
```python
import os
print(os.getcwd())  # Check current directory
items = PortfolioLoader.load_from_csv('/full/path/to/portfolio.csv')
```

### "Stage not recognized"

**Solution:** Ensure stage values are "Stage 1", "Stage 2", or "Stage 3" (or just "1", "2", "3")

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Review [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for feature coverage
- Check [PHASE_4_SUMMARY.md](PHASE_4_SUMMARY.md) for scenario analysis details
- Explore example scripts in `examples/` directory

## Support

For questions or issues:
- Check the documentation in README.md
- Review example scripts in `examples/`
- Check test cases in `tests/` for usage patterns

## Configuration

Customize calculations by editing:
- `config/default_config.yaml` - ECL calculation parameters
- `config/scenarios_config.yaml` - Economic scenarios

## Key Metrics Explained

- **ECL (Expected Credit Loss)**: The probability-weighted amount expected to be lost
- **Coverage Ratio**: ECL as % of total exposure (higher = more conservative)
- **Stage 1**: Performing loans (12-month ECL)
- **Stage 2**: Significant increase in credit risk (lifetime ECL)
- **Stage 3**: Credit-impaired loans (lifetime ECL)

## Example Output

```
Total ECL:          $113,983.39
Total Exposure:     $29,210,000.00
Coverage Ratio:     0.39%

Stage Distribution:
  Stage 1: 16 items, $23.8M (81.7%)
  Stage 2:  5 items, $ 3.7M (12.4%)
  Stage 3:  4 items, $ 1.7M ( 5.8%)

ECL by Sector:
  Healthcare      $34,668.74 (30.4%)
  Manufacturing   $23,921.16 (21.0%)
  Energy          $17,375.07 (15.2%)
```

Happy modeling! 🚀
