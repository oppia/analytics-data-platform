# Dimension Layer (`dim/`)

The Dimension Layer maintains descriptive master attribute reference context across the analytics workspace, mapping structural attributes like user profiles, lesson categories, and interaction objects.

## Structural Requirements
* Optimally structured for downstream joins against transactional tables (`fct/`).
* Standardized to maintain high readability and clean categorical groupings.
* Designed to track slow-moving historical attribute properties securely.
