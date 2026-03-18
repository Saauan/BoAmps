# BoAmps Data Model Reference

BoAmps reports are JSON objects. Fields marked **bold** in the Required column are required (or required if the parent object is present).

## Top-level structure

| Field | Type | Required |
|---|---|---|
| header | object | no |
| **task** | object | **yes** |
| **measures** | array | **yes** |
| system | object | no |
| software | object | no |
| **infrastructure** | object | **yes** |
| environment | object | no |
| quality | string (enum) | no — `high`, `medium`, `low` |

---

## header

| Field | Type | Required | Notes |
|---|---|---|---|
| licensing | string | no | e.g. `Creative Commons 4.0` |
| formatVersion | string | no | e.g. `0.1` |
| formatVersionSpecificationUri | string | no | |
| reportId | string | no | Prefer UUID4 |
| **reportDatetime** | string | **yes** | `YYYY-MM-DD HH:MM:SS` |
| reportStatus | string (enum) | no | `draft`, `final`, `corrective`, `other` |

### header.publisher

| Field | Type | Required | Notes |
|---|---|---|---|
| name | string | no | Organization name |
| division | string | no | Department |
| projectName | string | no | |
| **confidentialityLevel** | string (enum) | **yes** | `public`, `internal`, `confidential`, `secret` |
| publicKey | string | no | Cryptographic public key |

---

## task

| Field | Type | Required | Notes |
|---|---|---|---|
| **taskStage** | string | **yes** | `inference`, `training`, `finetuning`, `preprocessing`, etc. |
| **taskFamily** | string | **yes** | e.g. `chatbot`, `text classification`, `image generation` |
| nbRequest | number | no | Number of inference requests (inference stage only) |
| **algorithms** | array | **yes** | See below. Usually 1 item. |
| **dataset** | array | **yes** | See below. Typically 2 items: input + output. |
| measuredAccuracy | number | no | 0–1 |
| estimatedAccuracy | string (enum) | no | `veryPoor`, `poor`, `average`, `good`, `veryGood` |
| taskDescription | string | no | Free text |

### task.algorithms[N]

Usually only `algorithms[0]` is needed. Add more items only if the task genuinely uses multiple distinct algorithms.

| Field | Type | Notes |
|---|---|---|
| trainingType | string | `supervisedLearning`, `unsupervisedLearning`, `reinforcementLearning`, `transferLearning`, etc. |
| algorithmType | string | `llm`, `nlp`, `neural network`, `rag`, `embeddings`, etc. |
| algorithmName | string | Leave empty if using a foundation model; fill `foundationModelName` instead |
| algorithmUri | string | Public URL to model |
| foundationModelName | string | e.g. `llama2-13b`, `gpt4-o` |
| foundationModelUri | string | HuggingFace URL, etc. |
| parametersNumber | number | Billions of parameters (e.g. `13` for a 13B model) |
| framework | string | e.g. `vllm`, `pytorch`, `sklearn` |
| frameworkVersion | string | |
| classPath | string | e.g. `sklearn.ensemble.RandomForestClassifier` |
| layersNumber | number | Deep learning only |
| epochsNumber | number | Training only |
| optimizer | string | e.g. `adam`, `lora`, `gridSearch` |
| quantization | string | e.g. `fp32`, `fp16`, `int8` |

### task.dataset[N]

Typical pattern: `dataset[0]` = input data, `dataset[1]` = output data.

| Field | Type | Required | Notes |
|---|---|---|---|
| **dataUsage** | string (enum) | **yes** | `input`, `output` |
| **dataType** | string (enum) | **yes** | `tabular`, `audio`, `boolean`, `image`, `video`, `object`, `text`, `token`, `word`, `other` |
| dataFormat | string (enum) | no | File format: `csv`, `json`, `parquet`, `png`, `text`, `xlsx`, `yaml`, `other`, … (full list in schema) |
| dataSize | number | no | Size in GB |
| dataQuantity | number | no | Number of items (tokens, images, rows, etc.) |
| shape | string | no | e.g. `(12, 1000)` |
| source | string (enum) | no | `public`, `private`, `other` |
| sourceUri | string | no | |
| owner | string | no | |

---

## measures[N]

One item per measurement method (or per hardware component if measuring separately). At minimum, one item is required.

| Field | Type | Required | Notes |
|---|---|---|---|
| **measurementMethod** | string | **yes** | `codecarbon`, `carbonai`, `wattmeter`, `azure metrics`, `ovh metrics`, etc. |
| manufacturer | string | no | Wattmeter manufacturer |
| version | string | no | Tool version |
| cpuTrackingMode | string | no | `constant`, `rapl` |
| gpuTrackingMode | string | no | `constant`, `nvml` |
| averageUtilizationCpu | number | no | 0–1 |
| averageUtilizationGpu | number | no | 0–1 |
| powerCalibrationMeasurement | number | no | kWh |
| durationCalibrationMeasurement | number | no | Seconds |
| **powerConsumption** | number | **yes** | kWh |
| measurementDuration | number | no | Seconds |
| measurementDateTime | string | no | `YYYY-MM-DD HH:MM:SS` |

---

## system

| Field | Type | Required |
|---|---|---|
| **os** | string | **yes** — e.g. `linux`, `windows`, `macos` |
| distribution | string | no — e.g. `ubuntu` |
| distributionVersion | string | no — e.g. `22.04` |

## software

| Field | Type | Required |
|---|---|---|
| **language** | string | **yes** — e.g. `python` |
| version | string | no — e.g. `3.10.12` |

---

## infrastructure

| Field | Type | Required | Notes |
|---|---|---|---|
| **infraType** | string (enum) | **yes** | `publicCloud`, `privateCloud`, `onPremise`, `other` |
| cloudProvider | string | no | `aws`, `azure`, `google`, `ovh`, etc. |
| cloudInstance | string | no | e.g. `a1.large` |
| cloudService | string | no | AI cloud service name |
| **components** | array | **yes** | See below |

### infrastructure.components[N]

One item per hardware type. Common pattern: one CPU item + one GPU item + one RAM item.

| Field | Type | Required | Notes |
|---|---|---|---|
| componentName | string | no | Human-readable, e.g. `2 x Tesla V100S-PCIE-32GB` |
| **componentType** | string | **yes** | `cpu`, `gpu`, `ram`, `hdd`, `ssd` |
| **nbComponent** | integer | **yes** | Number of units of this component |
| memorySize | number | no | GB per unit (not total). For GPU embedded memory; do not use for RAM here. |
| manufacturer | string | no | e.g. `nvidia`, `intel` |
| family | string | no | e.g. `geforce`, `xeon` |
| series | string | no | e.g. `gtx1080`, `gold 6226r` |
| share | number | no | 0–1. Fraction of hardware used by this task. Default: `1`. |

---

## environment

| Field | Type | Required | Notes |
|---|---|---|---|
| **country** | string | **yes** | e.g. `france` |
| latitude | number | no | |
| longitude | number | no | |
| location | string | no | City, region, or datacenter name |
| powerSupplierType | string (enum) | no | `public`, `private`, `internal`, `other` |
| powerSource | string (enum) | no | `solar`, `wind`, `nuclear`, `hydroelectric`, `gas`, `coal`, `other` |
| powerSourceCarbonIntensity | number | no | gCO2eq/kWh |

---

## Concrete example

See `boamps-repo/examples/energy-report-llm-inference.json` for a complete valid report.

That example's structure at a glance:
- 1 algorithm (`llm`, foundation model `llama2-13b`, framework `vllm`)
- 2 datasets: `dataset[0]` = input tokens (11), `dataset[1]` = output tokens (828)
- 1 measure (`codecarbon`, with `cpuTrackingMode` and `gpuTrackingMode`)
- 3 components: CPU (`Intel Xeon Gold 6226R`, 30 cores) + GPU (`Tesla V100S`, 2 units, 32 GB each) + RAM (86 GB)
- Environment: `france`, `powerSupplierType: public`
