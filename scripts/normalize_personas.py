#!/usr/bin/env python3
"""批量规范化 persona：初始好感 80，补全身体部位敏感度。"""

from __future__ import annotations

from pathlib import Path

import yaml

PERSONA_DIR = Path(__file__).resolve().parents[1] / "config" / "personas"

DEFAULT_AFFECTION = 80
DEFAULT_SENSITIVITY = {
    "neck": 5,
    "ears": 5,
    "lips": 5,
    "chest": 5,
    "waist": 6,
    "back": 4,
    "hips": 5,
    "thighs": 6,
    "inner_thigh": 6,
}
BROTHER_SENSITIVITY = {
    "neck": 3,
    "ears": 2,
    "lips": 1,
    "chest": 2,
    "waist": 3,
    "back": 3,
    "hips": 2,
    "thighs": 3,
    "inner_thigh": 2,
}


def merge_sensitivity(existing: dict | None, defaults: dict) -> dict:
    merged = dict(defaults)
    if existing:
        merged.update({k: int(v) for k, v in existing.items()})
    return merged


def normalize_file(path: Path) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return False

    intimate = data.setdefault("intimate_state", {})
    intimate["affection"] = DEFAULT_AFFECTION

    rel_type = data.get("relationship_type", "romance")
    defaults = BROTHER_SENSITIVITY if rel_type == "brotherhood" else DEFAULT_SENSITIVITY
    intimate["sensitivity"] = merge_sensitivity(intimate.get("sensitivity"), defaults)

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )
    return True


def main() -> None:
    count = 0
    for yaml_file in sorted(PERSONA_DIR.glob("*.yaml")):
        if normalize_file(yaml_file):
            count += 1
            print(f"updated {yaml_file.name}")
    print(f"done: {count} personas")


if __name__ == "__main__":
    main()
