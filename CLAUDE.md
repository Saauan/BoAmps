# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BoAmps** is a standard for reporting AI/ML model energy consumption. It defines a JSON schema for energy reports and provides tools to validate, generate, and convert these reports.

## Common Commands

### Schema Validation
```bash
cd tools/schema_validator/
pip install -r requirements.txt
python validate-schema.py ../../examples/energy-report-llm-inference.json
```

### JSON Report Generation from CodeCarbon CSV (2-step)
```bash
cd tools/json_generator/bash/

# Step 1: Generate pre-filled text form
./gen_form.sh -a ./data/conf/boamps_auto_prefill_codecarbon.csv \
              ./data/conf/config_nb_fields_boamps.conf \
              ./data/input/codecarbon_file.csv 1 > output.txt

# Step 2: Convert form to JSON
./form2json.sh -a ./data/conf/boamps_auto_prefill_codecarbon.csv output.txt > report.json
```

### JSON to CSV Flattening
```bash
cd tools/data_flattener/
python flatten_json_to_csv.py ../../examples/energy-report-llm-inference.json report.csv
```

## Architecture

### Core Data Model (`model/`)

Five interdependent JSON schemas compose a complete energy report:
- `report_schema.json` — Top-level report with `$ref` links to the sub-schemas below
- `algorithm_schema.json` — ML model/algorithm description (type, framework, quantization, etc.)
- `dataset_schema.json` — Input/output dataset properties (type, format, size, source)
- `hardware_schema.json` — Infrastructure components (CPU, GPU, RAM, etc.)
- `measure_schema.json` — Energy measurement details (method, tracking mode, kWh, duration)

A report contains: `header`, `task`, `algorithms[]`, `dataset[]`, `measures[]`, `system`, `software`, `infrastructure`, `environment`, `quality`.

### Tools

**`tools/schema_validator/`** — Python script using `jsonschema` to validate any JSON report against `model/report_schema.json`.

**`tools/json_generator/bash/`** — Bash pipeline that converts tool-specific CSV output (e.g., CodeCarbon) into BoAmps JSON:
- `gen_form.sh` produces a human-readable text form (editable before conversion)
- `form2json.sh` converts the text form to valid JSON
- Configuration files in `data/conf/` map source CSV columns to BoAmps schema fields; editing these enables support for new measurement tools

**`tools/data_flattener/`** — Python script that flattens a nested BoAmps JSON report to a single CSV row for dataset aggregation.

### Data Flow
```
Measurement tool (CodeCarbon, PyJoules, wattmeter…)
  → CSV output
  → gen_form.sh → editable text form
  → form2json.sh → BoAmps JSON
  → validate-schema.py (validation)
  → flatten_json_to_csv.py → CSV row → HuggingFace dataset
```

## Key Configuration

`tools/json_generator/bash/data/conf/boamps_auto_prefill_codecarbon.csv` — Field-mapping config that controls how source CSV columns map to BoAmps schema fields. Supports direct column references, fixed values, lists, and mixed static/dynamic values. Edit this file to add support for new measurement tools.

`tools/json_generator/bash/data/conf/config_nb_fields_boamps.conf` — Controls how many algorithm/dataset/measure sections are generated in the form.
