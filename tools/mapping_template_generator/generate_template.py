#!/usr/bin/env python3
"""
Generate a template mapping_info.csv from BoAmps JSON schemas.

The template pre-fills boamps_field, boamps_type, and required columns,
leaving source_field, source_type, transformation, static_value, and note empty
(except enum constraints, which are pre-filled in the note column).

Usage:
    python generate_template.py
    python generate_template.py --output /path/to/mapping_info_template.csv
"""

import argparse
import csv
import json
from pathlib import Path


COLUMNS = [
    "boamps_field",
    "boamps_type",
    "required",
    "source_field",
    "source_type",
    "transformation",
    "static_value",
    "note",
]


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ref_to_local_path(ref: str, model_dir: Path) -> Path:
    return model_dir / ref.split("/")[-1]


def make_row(path: str, boamps_type: str, is_required: bool, note: str = "") -> dict:
    return {
        "boamps_field": path,
        "boamps_type": boamps_type,
        "required": is_required,
        "source_field": "",
        "source_type": "",
        "transformation": "",
        "static_value": "",
        "note": note,
    }


def field_type_label(defn: dict) -> str:
    base = defn.get("type", "object")
    if "enum" in defn:
        return f"{base} (enum)"
    return base


def enum_note(defn: dict) -> str:
    if "enum" not in defn:
        return ""
    values = [str(v) for v in defn["enum"] if v is not None]
    return f"Allowed values: {', '.join(values)}"


def flatten_properties(
    properties: dict,
    required_fields: list[str],
    prefix: str,
    model_dir: Path,
) -> list[dict]:
    rows = []
    for name, defn in properties.items():
        path = f"{prefix}.{name}" if prefix else name
        is_required = name in required_fields
        field_type = defn.get("type", "object")

        if field_type == "object" and "properties" in defn:
            sub_required = defn.get("required", [])
            rows.extend(flatten_properties(defn["properties"], sub_required, path, model_dir))

        elif field_type == "array":
            items = defn.get("items", {})
            ref = items.get("$ref")
            if ref:
                sub_schema = load_json(ref_to_local_path(ref, model_dir))
                sub_required = sub_schema.get("required", [])
                rows.extend(
                    flatten_properties(
                        sub_schema.get("properties", {}),
                        sub_required,
                        f"{path}[0]",
                        model_dir,
                    )
                )
            else:
                rows.append(make_row(path, field_type_label(defn), is_required, enum_note(defn)))

        else:
            rows.append(make_row(path, field_type_label(defn), is_required, enum_note(defn)))

    return rows


def generate_template(model_dir: Path) -> list[dict]:
    report_schema = load_json(model_dir / "report_schema.json")
    top_required = report_schema.get("required", [])
    return flatten_properties(report_schema["properties"], top_required, "", model_dir)


def write_csv(rows: list[dict], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Written {len(rows)} rows to {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: mapping_info_template.csv next to this script)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).parent
    model_dir = script_dir.parent.parent / "model"
    output_path = args.output or script_dir / "mapping_info_template.csv"

    rows = generate_template(model_dir)
    write_csv(rows, output_path)


if __name__ == "__main__":
    main()
