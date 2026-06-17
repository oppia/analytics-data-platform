# Oppia Product Analytics Data Platform

This repository houses the central dbt (Data Build Tool) transformation pipeline for Oppia. It ingests raw logging inputs from both the Web server and Android client applications and converts them into structured, performance-optimized analytical datasets inside Google Cloud BigQuery.

---

## 📂 Repository Topology

```text
├── .github/workflows/       # Automated CI/CD execution runs (PR validation & Weekly deploys)
├── macros/                  # Global reusable SQL compilation modules (e.g., surrogate keys)
├── models/                  # Core transformation layers
│   ├── stg/                 # Staging: Source cleaning and 1:1 type casting
│   ├── dim/                 # Dimensions: Contextual master reference tables
│   ├── fct/                 # Facts: Immutable time-series action logs
│   └── agg/                 # Aggregations: High-performance dashboard rollups
├── dbt_project.yml          # Core routing configurations and project scope
└── profiles.yml.example     # Blueprint for credential file configuration

