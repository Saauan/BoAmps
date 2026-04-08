---
name: boamps-converter
description: >
  Use this skill to implement a Python converter that transforms source energy measurement data
  into BoAmps JSON reports. Trigger when the user has a completed mapping_info.csv and
  mapping_extra_info.md (produced by the boamps-mapping skill) and is ready to write the
  conversion code. Also trigger when the user says "build the converter", "implement the BoAmps
  converter", "generate BoAmps reports from my data", or "turn my mapping into code" — even
  if they don't mention the skill by name. This skill produces a validated Python script that
  converts source files into schema-valid BoAmps JSON reports.
disable-model-invocation: true
---

# BoAmps Converter

This skill implements the Python converter described in `mapping_info.csv` and
`mapping_extra_info.md`. Read both files now, along with `references/boamps_model.md` and
`boamps-repo/examples/energy-report-llm-inference.json`, before writing any code.

## Checklist

Copy this into your response and check off steps as you go:

- [ ] Step 0 — Load context (mapping files + model reference + example)
- [ ] Step 1 — Write the converter
- [ ] Step 2 — Test on a single row
- [ ] Step 3 — Batch convert all source files
- [ ] Step 4 — Validate all reports
- [ ] Step 5 — Iterate until all reports are clean

---

## Step 0 — Load context

Read these files before writing anything. Use the **Read tool directly** — do not spawn agents or
subagents for this step.

1. `mapping_info.csv` — in the **argument directory** (the path the user passed to this skill)
2. `mapping_extra_info.md` — same directory as `mapping_info.csv`
3. `references/boamps_model.md` — in this skill's own `references/` folder
4. `boamps-repo/examples/energy-report-llm-inference.json` — reference for what a valid report looks like

Ensure the venv is active:
```bash
source boamps-repo/.venv/bin/activate
```

---

## Step 1 — Write the converter

Create `converter.py`. Use a **functional paradigm** throughout — pure functions, no classes.

### CLI interface

```bash
python converter.py data/run_*.csv
python converter.py data/run_*.csv --output reports/
```

The script takes source files as positional arguments (the shell expands globs before passing
them in). Add an `--output` flag for the reports directory (default: `./reports/`).

### Data loading

Load all source files into a single polars DataFrame. Adapt format as needed:

```python
import polars as pl

def load_sources(files: list[str]) -> pl.DataFrame:
    return pl.concat([pl.read_csv(f) for f in files])
```

For JSON or other formats, follow what `mapping_extra_info.md` specifies.

### Report-building functions

Write one pure function per top-level BoAmps section. Each takes a single row (as a dict or
polars `Row`) and returns a Python dict. Compose them in a top-level `build_report` function:

```python
def build_header(row: dict) -> dict: ...
def build_task(row: dict) -> dict: ...
def build_algorithms(row: dict) -> list[dict]: ...
def build_dataset(row: dict) -> list[dict]: ...
def build_measures(row: dict) -> list[dict]: ...
def build_system(row: dict) -> dict: ...
def build_software(row: dict) -> dict: ...
def build_infrastructure(row: dict) -> dict: ...
def build_components(row: dict) -> list[dict]: ...
def build_environment(row: dict) -> dict: ...

def build_report(row: dict) -> dict:
    return {
        "header": build_header(row),
        "task": {
            **build_task(row),
            "algorithms": build_algorithms(row),
            "dataset": build_dataset(row),
        },
        "measures": build_measures(row),
        "system": build_system(row),
        "software": build_software(row),
        "infrastructure": {
            **build_infrastructure(row),
            "components": build_components(row),
        },
        "environment": build_environment(row),
        "quality": ...,
    }
```

**Three important rules:**
- **Omit optional fields when their value is None or empty.** Do not write `"field": None` into
  the JSON — this can cause schema validation failures for typed fields.
- **When a source column is null for some rows, check for a fallback.** If `mapping_info.csv`
  maps a field to a column that is null for certain rows, look for a secondary column that
  carries equivalent information for those rows and fall back to it. For example, a detailed
  `model_full` column might only be populated for server rows, while a simpler `model` column
  covers all rows — use whichever is available rather than writing `"None"` or omitting a
  field that could be populated.
- **Generate a fresh UUID4 for `header.reportId`** for each report:
  ```python
  import uuid
  str(uuid.uuid4())
  ```

### Saving reports

Use this filename convention (unless `mapping_extra_info.md` specifies otherwise):

```
report_{publisher}_{taskStage}_{taskFamily}_{infraType}_{custom-id}.json
```

The `custom-id` can be any string that makes the filename unique and descriptive for the project.
Prefer something human-readable that encodes the key dimensions of variation in the dataset —
for example `{project}_{machine_type}_{model_name}_{quant}` for a model benchmarking dataset.
Avoid falling back to a bare UUID unless no better identifier exists.

**Uniqueness check:** after generating all files, assert that the number of output files equals
the number of source rows. If there are fewer files, your filename convention has collisions —
add a distinguishing column (e.g. model size in billions, dataset name, repetition index) until
filenames are unique across all rows.

Pretty-print each report with `json.dumps(report, indent=2)`.

---

## Step 2 — Test on a single row per variant

If the source data has distinct row types (e.g. different platforms, machine types, or
configurations), test one representative row per type — not just the first row. A bug in a
conditional branch that only affects one variant will be invisible if you only test rows from
another. Print each result to stdout and inspect:

- Does the top-level structure look right (`task`, `measures`, `infrastructure` present)?
- Are required fields present and non-null?
- Are values in the right format — units correct, datetimes as `YYYY-MM-DD HH:MM:SS`, enum
  values matching exactly?
- Are there any `None` or `"None"` values that leaked into the output? (A column value of
  Python `None` cast to `str()` silently becomes `"None"` — always guard with an explicit
  null check before stringifying.)

Fix any issues before proceeding to batch conversion.

---

## Step 3 — Batch convert all source files

Once the single-row test passes, run the converter on all source files:

```bash
python converter.py path/to/data/*.csv --output reports/
```

---

## Step 4 — Validate all reports

The BoAmps schema validator uses relative paths internally, so it **must be run with its working
directory set to `boamps-repo/tools/schema_validator/`**. Running it from the reports directory
will fail with a file-not-found error. Use Python's `subprocess` with `cwd` to handle this:

```python
import subprocess, sys
from pathlib import Path
from collections import defaultdict

reports_dir = Path("boamps_reports")
validator_dir = Path("boamps-repo/tools/schema_validator")
validator = validator_dir / "validate-schema.py"

errors_by_msg = defaultdict(list)
clean = 0
reports = sorted(reports_dir.glob("*.json"))

for rpt in reports:
    result = subprocess.run(
        [sys.executable, str(validator), str(rpt.resolve())],
        capture_output=True, text=True, cwd=str(validator_dir)
    )
    if result.returncode == 0:
        clean += 1
    else:
        errors_by_msg[(result.stdout + result.stderr).strip()].append(rpt.name)

print(f"Clean: {clean}/{len(reports)}")
for msg, files in sorted(errors_by_msg.items(), key=lambda x: -len(x[1])):
    print(f"\n[{len(files)} reports] {msg[:400]}")
    print("  e.g.", files[0])
```

**Aggregate errors before reporting.** Group failures by the failing field path. A pattern like:

> 47 reports fail on `task.algorithms[0].parametersNumber` — expected number, got string

is far more actionable than 47 individual error messages. Summarise the groups and their counts.

---

## Step 5 — Iterate until clean

For each group of validation errors:

1. Identify the root cause in the relevant `build_*` function — wrong type, wrong format,
   missing required field, invalid enum value, None leaking through.
2. Fix the function.
3. Re-run the batch conversion and validation.

Repeat until the validator produces no errors across all reports.

When clean, report to the user:
- Total reports generated
- Zero-error confirmation
- Output directory path
