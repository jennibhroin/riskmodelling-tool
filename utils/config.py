"""Configuration management for IFRS 9 ECL system."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class Config:
    """Configuration manager for ECL system.

    Loads configuration from YAML files and environment variables.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to configuration YAML file
        """
        self._config: Dict[str, Any] = {}
        self._load_defaults()

        if config_path:
            self.load_from_file(config_path)

        # Load environment variables
        load_dotenv()

    def _load_defaults(self):
        """Load default configuration."""
        self._config = {
            'ecl': {
                'calculation_method': 'individual',
                'time_horizon_stages': {
                    'stage_1': 12,
                    'stage_2': 'lifetime',
                    'stage_3': 'lifetime',
                },
                'sicr_thresholds': {
                    'pd_increase_bps': 30,
                    'relative_increase_pct': 200,
                    'days_past_due': 30,
                },
                'discount_rate': 0.05,  # 5% discount rate for present value
            },
            'staging': {
                'days_past_due_threshold': 30,
                'days_past_due_default': 90,
                'cure_period': 3,
            },
            'pd': {
                'credit_score_min': 300,
                'credit_score_max': 850,
                'floor': 0.0001,  # 1 bp minimum PD
                'ceiling': 0.99,  # 99% maximum PD
            },
            'lgd': {
                'unsecured_base': 0.45,  # 45% base LGD for unsecured
                'secured_base': 0.25,  # 25% base LGD for secured
                'collateral_haircuts': {
                    'real_estate': 0.20,
                    'equipment': 0.30,
                    'inventory': 0.40,
                    'receivables': 0.25,
                    'securities': 0.15,
                    'cash': 0.00,
                },
                'downturn_multiplier': 1.25,  # 25% increase in downturn
                'floor': 0.01,  # 1% minimum LGD
                'ceiling': 1.00,  # 100% maximum LGD
            },
            'ead': {
                'ccf': 0.75,  # Credit conversion factor for undrawn commitments
                'ccf_by_product': {
                    'credit_card': 0.50,
                    'revolving_credit': 0.75,
                    'term_loan': 1.00,
                    'overdraft': 0.50,
                },
            },
            'scenarios': {
                'default_scenarios': [
                    {'name': 'base', 'probability': 0.50},
                    {'name': 'optimistic', 'probability': 0.25},
                    {'name': 'pessimistic', 'probability': 0.25},
                ],
            },
            'macro_variables': {
                'gdp_growth': 2.5,
                'unemployment_rate': 4.0,
                'interest_rate': 2.5,
                'credit_spreads': 150,
            },
            'output': {
                'decimal_places': 2,
                'currency_symbol': '$',
                'large_number_format': 'millions',  # 'thousands', 'millions', 'billions'
            },
        }

    def load_from_file(self, file_path: str):
        """Load configuration from YAML file.

        Args:
            file_path: Path to YAML configuration file
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        with open(path, 'r') as f:
            file_config = yaml.safe_load(f)

        # Merge with existing config (file config takes precedence)
        self._merge_config(self._config, file_config)

    def _merge_config(self, base: Dict, update: Dict):
        """Recursively merge configuration dictionaries.

        Args:
            base: Base configuration dictionary
            update: Update configuration dictionary
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'ecl.sicr_thresholds.pd_increase_bps')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """Set configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'ecl.discount_rate')
            value: Value to set
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section.

        Args:
            section: Section name (e.g., 'ecl', 'staging')

        Returns:
            Configuration section dictionary
        """
        return self._config.get(section, {})

    def to_dict(self) -> Dict[str, Any]:
        """Get entire configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        return self._config.copy()

    def save_to_file(self, file_path: str):
        """Save configuration to YAML file.

        Args:
            file_path: Path to output YAML file
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)


# Global config instance
_global_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance.

    Returns:
        Global Config instance
    """
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def set_config(config: Config):
    """Set global configuration instance.

    Args:
        config: Config instance to set as global
    """
    global _global_config
    _global_config = config
