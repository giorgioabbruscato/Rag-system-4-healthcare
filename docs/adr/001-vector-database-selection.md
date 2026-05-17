# ADR 001: Vector Database Selection

- **Status**: Accepted
- **Date**: 2026-05-17

## Context
The project needs a vector database for clinical embeddings, with support for semantic search over cases and guidelines. The storage layer must work locally for development, be easy to containerize, and support named vectors for multimodal or multi-space retrieval.

## Decision
Use **Qdrant** as the vector database.

## Alternatives Considered
- **ChromaDB**: simple local setup, but weaker fit for the project’s retrieval patterns and deployment goals.
- **FAISS**: fast ANN search, but it is a library rather than a managed vector database and would require more surrounding infrastructure.
- **Pinecone**: strong hosted option, but not aligned with the project’s local-first and Docker-first requirements.

## Consequences
- Works well in local and containerized environments.
- Supports named vectors and REST APIs, which fit the current architecture.
- Keeps the project ready for future server-based deployment if needed.
- Introduces an implementation dependency on the Qdrant client/wrapper used by the project codebase.

## Notes
This choice is already reflected in the dataset indexing and retrieval flow documented in the main README.