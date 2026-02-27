"""Setup script for IFRS 9 ECL system."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="ifrs9-ecl-system",
    version="1.0.0",
    description="Advanced IFRS 9 Expected Credit Loss (ECL) risk modeling system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ECL Risk Team",
    author_email="risk@example.com",
    url="https://github.com/example/ifrs9-ecl-system",
    packages=find_packages(exclude=["tests", "tests.*", "examples"]),
    python_requires=">=3.8",
    install_requires=[
        "pandas>=2.1.0",
        "numpy>=1.25.0",
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
        "pydantic>=2.4.0",
        "openpyxl>=3.1.2",
        "pyarrow>=13.0.0",
        "matplotlib>=3.8.0",
        "seaborn>=0.13.0",
        "plotly>=5.17.0",
        "jinja2>=3.1.2",
        "xlsxwriter>=3.1.9",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
        "structlog>=23.1.0",
        "click>=8.1.7",
        "tqdm>=4.66.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-benchmark>=4.0.0",
            "hypothesis>=6.88.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ifrs9-ecl=main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="ifrs9 ecl expected-credit-loss risk-modeling banking finance",
    project_urls={
        "Bug Reports": "https://github.com/example/ifrs9-ecl-system/issues",
        "Source": "https://github.com/example/ifrs9-ecl-system",
        "Documentation": "https://github.com/example/ifrs9-ecl-system/wiki",
    },
)
