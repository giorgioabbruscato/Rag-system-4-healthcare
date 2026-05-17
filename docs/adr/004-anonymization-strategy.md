# ADR 004: Anonymization Strategy

- **Status**: Accepted
- **Date**: 2026-05-17

## Context
The project handles medical imaging data, so privacy requirements are central. The anonymization approach must satisfy GDPR/HIPAA expectations while remaining deterministic enough for reproducible processing and testing.

## Decision
Use a privacy-by-design anonymization pipeline based on:
- hash-based case identifiers,
- DICOM tag stripping,
- automated verification of the derived dataset.

## Alternatives Considered
- **Manual anonymization**: too error-prone and difficult to scale.
- **Partial metadata redaction**: not strict enough for publication and testing.
- **Full synthetic replacement**: safer in some settings, but unnecessary for this project’s current scope.

## Consequences
- Patient-identifying fields are removed before derived artifacts are published.
- Case identifiers remain stable across the pipeline without exposing source identities.
- Verification becomes part of the workflow, reducing the chance of accidental leakage.
- The dataset is easier to share in a public portfolio context.

## Notes
See [ANONYMIZATION.md](../../ANONYMIZATION.md) for the operational details of the anonymization pipeline.