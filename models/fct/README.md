# Fact Layer (`fct/`)

The Fact Layer models discrete event tracking structures, system interactions, and time-series metrics. These tables capture core chronological event operations, such as session updates, answers, and interactions.

## Subfolder Organization
* `web/`: Platform-specific structures processing web application metrics.
* `android/`: Platform-specific components handling mobile event logs.
* `core/`: Uniform models shared across both platforms where input fields align perfectly.

## Production Design Guidelines
* Granular records represent single measurable actions.
* Joins should target primary record streams with reference lookup assets (`dim/`).
* Primary records must utilize descriptive, unique identifier labels using the format `{entity}_id` or deterministic business key hashes.
