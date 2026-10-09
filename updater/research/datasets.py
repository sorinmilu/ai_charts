"""Dataset registry: ID prefixes, inclusion units, and classification rubrics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class InclusionUnit(str, Enum):
    PUBLICATION = "publication"
    CLAIM = "claim"


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    relative_path: str
    id_prefix: str
    inclusion_unit: InclusionUnit
    level_labels: dict[str, str]
    unclassified_label: str | None
    allows_unclassified: bool
    additions_basename: str
    report_basename: str
    is_trajectory: bool = False
    has_type_column: bool = False


# Labels keyed by level string ("-3".."3") or "" for unclassified.
CAPABILITY = DatasetSpec(
    key="capability",
    relative_path="web-app/data/ai_capability_talking_points.csv",
    id_prefix="CAP",
    inclusion_unit=InclusionUnit.PUBLICATION,
    level_labels={
        "-3": "Strongly negative",
        "-2": "Moderately negative",
        "-1": "Slightly negative",
        "0": "Neutral / mixed / unresolved",
        "1": "Slightly positive",
        "2": "Moderately positive",
        "3": "Strongly positive",
    },
    unclassified_label=None,
    allows_unclassified=False,
    additions_basename="current_capability_additions.csv",
    report_basename="current_capability_update_report.md",
    has_type_column=True,
)

UTILITY = DatasetSpec(
    key="utility",
    relative_path="web-app/data/ai_practical_utility_talking_points.csv",
    id_prefix="UTL",
    inclusion_unit=InclusionUnit.PUBLICATION,
    level_labels={
        "-3": "Highly counterproductive",
        "-2": "Moderately counterproductive",
        "-1": "Slightly counterproductive",
        "0": "No clear net benefit / mixed",
        "1": "Slightly useful",
        "2": "Moderately useful",
        "3": "Highly useful",
        "": "Unclassified — insufficient evidence of net utility",
    },
    unclassified_label="Unclassified — insufficient evidence of net utility",
    allows_unclassified=True,
    additions_basename="practical_utility_additions.csv",
    report_basename="practical_utility_update_report.md",
)

ECONOMIC = DatasetSpec(
    key="economic",
    relative_path="web-app/data/ai_economic_impact_talking_points.csv",
    id_prefix="ECO",
    inclusion_unit=InclusionUnit.CLAIM,
    level_labels={
        "-3": "Middle class substantially worse off",
        "-2": "Middle class moderately worse off",
        "-1": "Middle class slightly worse off",
        "0": "Little change or mixed effects",
        "1": "Middle class slightly better off",
        "2": "Middle class moderately better off",
        "3": "Middle class substantially better off",
        "": "Unclassified: insufficient directional evidence",
    },
    unclassified_label="Unclassified: insufficient directional evidence",
    allows_unclassified=True,
    additions_basename="middle_class_economics_additions.csv",
    report_basename="middle_class_economics_update_report.md",
)

JOBS = DatasetSpec(
    key="jobs",
    relative_path="web-app/data/ai_intellectual_jobs_talking_points.csv",
    id_prefix="JOB",
    inclusion_unit=InclusionUnit.CLAIM,
    level_labels={
        "-3": "Widespread job disappearance",
        "-2": "Substantial job reduction",
        "-1": "Limited job reduction",
        "0": "Broadly stable employment",
        "1": "Limited job growth",
        "2": "Substantial job growth",
        "3": "Large-scale job expansion",
        "": "Unclassified — insufficient net-employment conclusion",
    },
    unclassified_label="Unclassified — insufficient net-employment conclusion",
    allows_unclassified=True,
    additions_basename="intellectual_jobs_additions.csv",
    report_basename="intellectual_jobs_update_report.md",
)

TRAJECTORY = DatasetSpec(
    key="trajectory",
    relative_path="web-app/data/ai_future_trajectory_talking_points.csv",
    id_prefix="T",
    inclusion_unit=InclusionUnit.CLAIM,
    level_labels={
        "-3": "Fundamental dead end",
        "-2": "Major limits ahead",
        "-1": "Slowing progress",
        "0": "Incremental development",
        "1": "Substantial further progress",
        "2": "Broad autonomous competence",
        "3": "Beyond human general capability",
        "": "Unclassified",
    },
    unclassified_label="Unclassified",
    allows_unclassified=True,
    additions_basename="future_trajectory_additions.csv",
    report_basename="future_trajectory_update_report.md",
    is_trajectory=True,
)

DATASETS_BY_PATH: dict[str, DatasetSpec] = {
    spec.relative_path: spec
    for spec in (CAPABILITY, UTILITY, ECONOMIC, JOBS, TRAJECTORY)
}


def spec_for_relative_path(relative_path: str) -> DatasetSpec | None:
    normalised = relative_path.replace("\\", "/").lstrip("./")
    return DATASETS_BY_PATH.get(normalised)


def resolve_dataset_file(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {relative_path} ({path})")
    return path
