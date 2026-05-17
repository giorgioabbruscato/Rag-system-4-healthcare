# ADR 002: Embedding Model

- **Status**: Accepted
- **Date**: 2026-05-17

## Context
The project needs an embedding model for clinical text and guideline retrieval. The model should run locally, avoid external API costs, and provide a good balance between quality, speed, and dimensionality.

## Decision
Use **all-MiniLM-L6-v2** as the default embedding model.

## Alternatives Considered
- **all-mpnet-base-v2**: higher quality in some retrieval scenarios, but heavier and slower.
- **OpenAI text-embedding-3-small**: strong quality, but introduces API dependency and ongoing cost.

## Consequences
- Embeddings can be generated offline and reproducibly.
- The model keeps the system lightweight enough for local development and demos.
- The embedding dimension stays at 384, which is simple to manage in the indexing pipeline.
- Retrieval quality is good for the current project scope, though future evaluation could justify a higher-capacity model.

## Notes
This decision matches the current technical summary in the README and the project’s local-first architecture.