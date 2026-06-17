# Oppia Product Analytics Data Platform

This repository houses the central dbt (Data Build Tool) transformation pipeline for Oppia. It ingests raw logging inputs from both the Web server and Android client applications and converts them into structured, performance-optimized analytical datasets inside Google Cloud BigQuery.

---

## 📂 Repository Topology

    ├── .github/workflows/      # Automated CI/CD execution runs (PR validation & Weekly deploys)
    ├── macros/                  # Global reusable SQL compilation modules (e.g., surrogate keys)
    ├── models/                  # Core transformation layers
    │   ├── stg/                 # Staging: Source cleaning and 1:1 type casting
    │   ├── dim/                 # Dimensions: Contextual master reference tables
    │   ├── fct/                 # Facts: Immutable time-series action logs
    │   └── agg/                 # Aggregations: High-performance dashboard rollups
    ├── dbt_project.yml          # Core routing configurations and project scope
    └── profiles.yml.example     # Blueprint for credential file configuration

---

## ⚙️ Local Sandbox Environment Setup

Before compiling data structures locally, developers must establish active credentials to access the development sandboxes inside `oppia-analytics-test`.

### 1. Initialize Authentication and Local Dependencies
Ensure you have Python 3.10+ installed globally, then initialize your analytics space:

    # Install core database compilation tools
    pip install dbt-bigquery

    # Pull down open-source external packages
    dbt deps

### 2. Configure Your Connection Profile
Local credentials are kept strictly out of git version control.

1. Copy the tracking template:
   cp profiles.yml.example profiles.yml

2. Open your newly created `profiles.yml` file and replace "dev_yourname" with your specific developer schema signature (e.g., dev_johndoe).

3. Authenticate with Google Cloud using your local user credentials:
   gcloud auth application-default login

### 3. Verify System Path Execution
Run a diagnostic framework check to ensure dbt can establish a secure handshake with BigQuery:

    dbt debug

---

## 🚀 Daily Execution Commands

* Compile the structural SQL lineage tree:
  dbt compile

* Build data tables inside your personal schema sandbox:
  dbt run --target dev

* Execute assertion tests against data quality constraints:
  dbt test --target dev

For full details regarding the analytics architecture, query writing structures, or production merge criteria, please read the documentation inside the [Models Directory README](models/README.md).
