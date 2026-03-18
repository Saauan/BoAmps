---
name: boamps-mapping
description: >
  Use this skill to design a mapping between source energy measurement data and the BoAmps
  standard report format. Trigger whenever the user wants to convert their energy data
  (CodeCarbon CSV, PyJoules output, wattmeter logs, experiment results, or any tabular format)
  into BoAmps JSON reports. Also trigger when the user mentions "BoAmps mapping",
  "mapping_info.csv", setting up a BoAmps pipeline, or standardizing their ML energy
  measurements — even if they don't say "mapping" explicitly. This skill produces
  mapping_info.csv and mapping_extra_info.md, which feed directly into the boamps-converter skill.
---

# BoAmps Mapping

This skill guides you through designing the mapping between source energy measurement data and
the BoAmps report standard. The result is two files:
- **`mapping_info.csv`** — field-by-field mapping table
- **`mapping_extra_info.md`** — everything needed to implement the converter that doesn't fit in a CSV

No converter code is written here from scratch. That's the job of the `boamps-converter` skill.
However, **if a `converter.py` already exists** in the working directory, note at the end of each
step which fields changed and update the converter to stay in sync — don't leave it stale.

Read `references/boamps_model.md` now for the full field reference before starting.

## Checklist

Copy this into your response and check off steps as you go:

- [ ] Step 0 — Setup (repo + venv)
- [ ] Step 1 — Read source data sample + detect nulls
- [ ] Step 2 — Clarify cardinality, array counts, units, platforms, and measurement tool
- [ ] Step 3 — Fill source column info (`source_field`, `source_type`)
- [ ] Step 4 — Design transformations (`transformation` column)
- [ ] Step 5 — Identify static values (`static_value` column)
- [ ] Step 6 — Write `mapping_extra_info.md`
- [ ] Step 7 — User review and sign-off

---

## Step 0 — Setup

Find the BoAmps repo. Check the current directory and common sibling paths first:

```bash
ls boamps-repo/ 2>/dev/null || ls ../boamps-repo/ 2>/dev/null || echo "not found"
```

If not found, clone it:
```bash
git clone https://github.com/Boavizta/BoAmps boamps-repo
```

Create a virtual environment if `boamps-repo/.venv` does not exist (adjust the path to wherever the repo lives):

```bash
python3 -m venv boamps-repo/.venv
source boamps-repo/.venv/bin/activate
pip install -r boamps-repo/tools/schema_validator/requirements.txt
pip install polars
```

If the venv already exists, just activate it:
```bash
source boamps-repo/.venv/bin/activate
```

---

## Step 1 — Read source data sample + detect nulls

**If the skill was invoked with a file path argument, use it directly.** Only ask the user if
no path was provided.

Read only the first 10–20 rows — not the whole file. The goal is to understand the schema.

```python
import polars as pl
df = pl.read_csv("path/to/data.csv", n_rows=20, null_values=["", "NA", "N/A", "null"])
print("Schema:", df.schema)
print(df.head(5))
```

Then inspect null patterns across the **full file** — columns with many nulls often indicate
platform-specific data that requires conditional fallback logic:

```python
df_full = pl.read_csv("path/to/data.csv", null_values=["", "NA", "N/A", "null"])
print("Total rows:", len(df_full))
print("Null counts:\n", df_full.null_count())
# For unique values, always drop nulls first to avoid type errors:
for col in df_full.columns:
    unique = df_full[col].drop_nulls().unique()
    if len(unique) <= 10:
        print(f"{col}: {sorted(unique.to_list())}")
```

Note which columns are null for certain rows only — these often correspond to a specific
platform or run type and will need CONDITIONAL handling in the mapping.

If any column names are unclear or ambiguous, ask the user before moving on.

---

## Step 2 — Clarify cardinality, array counts, units, platforms, and measurement tool

Before mapping, gather all of the following. Ask these questions together in a single message
rather than one at a time.

**Cardinality**
- Does one source row correspond to one BoAmps report, or do multiple rows need aggregating?

**Array sizes per report**
- How many algorithms? (Usually 1)
- How many datasets? (Typically 2: input + output — `dataset[0]` and `dataset[1]`)
- How many measure items? (Often 1)
- How many infrastructure components? (Usually CPU + GPU + RAM = 3 items)

**Energy units** *(always ask this explicitly)*
- What are the units of each energy and power column? (J, mJ, Wh, kWh, nAh, W, mW…)
  BoAmps `measures[].powerConsumption` must be in **kWh** — document the conversion formula.
- What are the units of duration columns? (s, ms…)
  BoAmps `measures[].measurementDuration` must be in **seconds**.

**Platform / environment discriminator** *(ask if there is a column like `machine_type`, `platform`, `device`, `env`)*
- If yes: list all distinct values and what each represents (hardware, OS, framework, etc.).
  Many BoAmps fields will be CONDITIONAL on this column — identify them early.

**Measurement tool** *(always ask this explicitly)*
- What tool or method was used to measure energy?
  (e.g. CodeCarbon, perf+RAPL, nvidia-smi, battery discharge API, INA260 wattmeter, custom…)
  This goes in `measures[].measurementMethod`, which is **required**.

**Input dataset type** *(for LLM inference tasks)*
- Is the input data tokens? If yes, is the input token count available in the source?
  See the "LLM inference patterns" section below.

---

## Step 3 — Fill source column info

Copy `assets/mapping_info_template.csv` to the working directory and rename it `mapping_info.csv`.

For each row, fill in:
- **`source_field`**: the column/key name in the source data. Leave empty for static or skipped fields.
- **`source_type`**: the data type as it appears in the source (e.g. `string`, `Float64`, `int`).

**Multi-platform / conditional fields**: If a field's value depends on a discriminator column
(e.g. `machine_type`), leave `source_field` and `static_value` empty and write
`CONDITIONAL — see mapping_extra_info.md` in the `note` column. Document the full lookup table
in `mapping_extra_info.md`. Typical conditionally-mapped fields: `measurementMethod`,
`cpuTrackingMode`, `framework`, `system.os`, `software.language`, `infraType`, all
`infrastructure.components[*]` rows.

If the cardinality analysis showed multiple items (e.g. 2 datasets, 3 components), duplicate
the relevant `[0]` rows and rename them `[1]`, `[2]`, etc. as needed.

---

## Step 4 — Design transformations

For each row where `source_field` is set, think through whether a transformation is needed:

- **Direct copy** — leave `transformation` empty
- **Unit conversion** — e.g. `/ 3600000` (J → kWh), `/ 1000` (ms → s)
- **Type cast** — e.g. `str()`, `int()`, `float()`
- **String parsing** — e.g. `strptime("%Y-%m-%d %H:%M:%S")`
- **Derived from multiple columns** — describe the logic (e.g. `nb_prompts * nb_repetitions * energy_per_prompt / 3600000`)
- **Lookup / conditional** — describe the logic; full table goes in `mapping_extra_info.md`
- **Null fallback** — if the primary column is null for some rows, describe the fallback:
  `col_a if col_a is not null else col_b * col_c`

Use the `note` column for clarifications. If any mapping requires a judgement call
(e.g. "should this be `tabular` or `token`?"), ask the user before deciding.

---

## Step 5 — Identify static values

Identify fields that are **constant across all reports** and not derived from the source.

For these rows, leave `source_field` and `transformation` empty and fill in `static_value`
with the literal value to use.

Ask the user to confirm or provide any static values you're unsure about. Common ones:
- `header.publisher.name`, `header.publisher.confidentialityLevel`
- `task.taskStage`, `task.taskFamily`
- `environment.country`, `environment.powerSupplierType`
- `quality`
- Any software/framework version not present in the source data

---

## Step 6 — Write mapping_extra_info.md

Create `mapping_extra_info.md` alongside `mapping_info.csv`. Structure it with these sections:

**Source Data** — file path, format, encoding, delimiter, multi-file structure if any.

**Row-to-Report Cardinality** — one-to-one or aggregation logic.

**Key Column Semantics** — a table of non-obvious columns: name, unit, description.
This is especially important for energy/power/duration columns whose units were confirmed in Step 2.

**Energy & Duration Conversions** — the exact formulas used to reach kWh and seconds,
with intermediate steps spelled out.

**Conditional Fields by `<discriminator_column>`** — for each CONDITIONAL field, a table:

| value | result |
|---|---|
| `platform_a` | `value_x` |
| `platform_b` | `value_y` |

**Infrastructure Components by `<discriminator_column>`** — full JSON blocks for each platform variant.

**Output** — output directory, file naming convention.

**Null Handling** — which columns can be null, for which rows, and what the fallback is.

**Assumptions to Confirm** — a numbered list of everything that was assumed and should be
verified by the user before running the converter. Organize by category:

1. *Units* — e.g. "`idle_powerdraw` is assumed to be in Watts, not Joules"
2. *Hardware specs* — e.g. "Pixel 8 has 8 GB RAM; iPhone 14 has 6 GB RAM"
3. *Timestamps* — e.g. "No experiment timestamp in source; using report generation date as placeholder"
4. *Licensing* — e.g. "`header.licensing` set to 'Creative Commons 4.0' — confirm if different"
5. *Software / framework versions* — e.g. "vllm version 0.7.3 assumed from known experiment setup"
6. *Measurement tool* — e.g. "measurementMethod for iOS set to 'ina260' — confirm tool name"

---

## Step 7 — User review and sign-off

Present a summary of:
- The cardinality and array structure decided in Step 2
- Source columns that mapped cleanly, and any that couldn't be mapped
- Static values that will be hard-coded
- All CONDITIONAL fields and which column drives them
- Any decisions that required assumptions

If a `converter.py` already exists in the working directory, also list the specific fields
that changed during this mapping session so the user knows what needs updating in the converter.
Do not rewrite the converter — just flag the deltas clearly.

Ask the user: *"Does this look right? Is there anything missing or incorrect before we move
to the converter?"*

**Do not proceed to implementation. Wait for explicit user confirmation.**

Once confirmed, tell the user:
> "The mapping is ready. You can now start a new conversation and invoke `/boamps-converter`
> with `mapping_info.csv` and `mapping_extra_info.md` in your working directory."

---

## LLM inference patterns

For LLM inference tasks, follow these conventions for `task.dataset[]`:

**Input dataset (`dataset[0]`):**
- If **input token count is available** in the source → `dataType: "token"`, `dataQuantity: <total input tokens>`
- If **token count is not available but prompt count is** → `dataType: "text"`, `dataQuantity: <number of prompts>`
- `dataQuantity` should represent the total across the full run (all prompts × all repetitions if applicable)

**Output dataset (`dataset[1]`):**
- `dataType: "token"`, `dataQuantity: <total output tokens>`
- If only mean tokens per generation is available: `round(nb_prompts * nb_repetitions * mean_tokens_per_generation)`

These distinctions matter for comparability across reports — token-level granularity is
preferred whenever available.
