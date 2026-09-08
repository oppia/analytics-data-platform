# Oppia Product Analytics Data Platform

This repository houses the central dbt (Data Build Tool) transformation pipeline for Oppia. It ingests raw logging inputs from both the Web server and Android client applications and converts them into structured, performance-optimized analytical datasets inside Google Cloud BigQuery.

---

## Repository Topology

The project uses three dbt model layers. Folder names are part of the dbt
configuration in `dbt_project.yml`, so new models should be added to the
corresponding layer.

  ├── models/
  │   ├── staging/
  │   │   ├── web/             # Raw web sources and web event cleaning
  │   │   ├── android/         # Raw Android sources and Android event cleaning
  │   │   └── cuj_reference/   # CUJ workbook inventory and step definitions
  │   ├── intermediate/        # Reusable transformations shared by marts
  │   │   └── cuj_health/      # CUJ mappings, readiness, progression, metrics
  │   └── marts/               # Business-facing models by product domain
  │       ├── users/
  │       ├── curriculum/
  │       ├── growth_outreach/
  │       └── cuj_health/      # Semantic Layer CUJ-health outputs
  ├── seeds/cuj_health/         # Governed CUJ mappings, thresholds, and step pairs
  ├── tests/cuj_health/         # Custom CUJ-health assertions
  ├── macros/                  # Reusable dbt macros across all domains
  │   ├── ga4/                 # Reusable GA4 event-parameter extraction
  │   ├── cuj_health/          # Shared CUJ-health calculations
  │   └── generate_surrogate_key.sql
  ├── utils/
  │   └── udf/                 # Warehouse user-defined functions
  ├── dbt_project.yml           # Model routing and project scope
  └── profiles.yml.example      # Credential configuration blueprint

### Model Naming

Use a double underscore between the entity and the business subject, for
example `stg_web_analytics__events` or `int_web_cuj__event_matches`. Keep
source definitions in `src_<platform>.yml` files and keep model descriptions
and tests beside the models they document.

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
