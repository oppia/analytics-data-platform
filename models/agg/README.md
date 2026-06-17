# Aggregation Layer (`agg/`)

The Aggregation Layer contains pre-aggregated, business-ready metric rollups optimized for fast analytical consumption via dashboard systems (e.g., Looker Studio).

### 🚨 Synchronization & Core Requirements
* **Dashboard Timestamp Rule:** To maintain complete operational clarity across Oppia teams, **every external dashboard view must prominently display a data refresh notice at the top of the report** referencing the system's runtime execution window.
* **Structural Split:** Files are explicitly isolated under `web/`, `android/`, or `core/` modules.
* **Platform Marker:** Every single model outputting from this layer must explicitly contain a populated `platform` text string column.
