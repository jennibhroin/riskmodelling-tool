"""Enumerations for IFRS 9 ECL calculations."""

from enum import Enum


class Stage(str, Enum):
    """IFRS 9 Credit Risk Stages.

    Stage 1: Performing loans with no significant increase in credit risk (12-month ECL)
    Stage 2: Significant increase in credit risk detected (lifetime ECL)
    Stage 3: Credit-impaired assets (lifetime ECL)
    """
    STAGE_1 = "Stage 1"
    STAGE_2 = "Stage 2"
    STAGE_3 = "Stage 3"

    def __str__(self) -> str:
        return self.value

    @property
    def is_performing(self) -> bool:
        """Check if stage represents performing asset."""
        return self in (Stage.STAGE_1, Stage.STAGE_2)

    @property
    def is_impaired(self) -> bool:
        """Check if stage represents credit-impaired asset."""
        return self == Stage.STAGE_3

    @property
    def uses_lifetime_ecl(self) -> bool:
        """Check if stage uses lifetime ECL (vs 12-month)."""
        return self in (Stage.STAGE_2, Stage.STAGE_3)


class ScenarioType(str, Enum):
    """Economic scenario types for forward-looking analysis."""
    BASE = "base"
    OPTIMISTIC = "optimistic"
    PESSIMISTIC = "pessimistic"
    STRESS = "stress"
    CUSTOM = "custom"

    def __str__(self) -> str:
        return self.value


class CalculationMethod(str, Enum):
    """ECL calculation methodology.

    INDIVIDUAL: Calculate ECL for each exposure individually
    COHORT: Group exposures by similar characteristics
    VINTAGE: Group exposures by origination period
    """
    INDIVIDUAL = "individual"
    COHORT = "cohort"
    VINTAGE = "vintage"

    def __str__(self) -> str:
        return self.value
