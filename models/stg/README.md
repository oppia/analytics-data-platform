# Staging Layer (`stg/`)

The Staging Layer acts as the operational entrance threshold for raw server logging data. It transforms raw database outputs into structurally sound datasets, removing source system anomalies before core downstream computation blocks execute.

## Layer Strategy & Requirements
* **Schema Blueprint**: Models map 1:1 against raw source tracking data tables.
* **Logic Constraints**: Limited to clean type casting, field naming standardization, and row filters. Business calculations or multi-table joins are prohibited.
* **Identity Standardization**: Every platform event mapping model must include three identity alignment keys:
  * `platform`: Explicit system label marker (`web` or `android`).
  * `local_user_id`: Native alphanumeric tracking ID string unique to the source server engine.
  * `global_user_id`: Consolidated cross-platform matching key using standard prefix strings (`web_12345`).
