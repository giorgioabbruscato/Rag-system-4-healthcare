# ADR 003: Multimodal RAG Strategy

- **Status**: Accepted
- **Date**: 2026-05-17

## Context
The system must analyze DICOM echocardiography cases using both textual clinical context and visual information from extracted frames. The architecture needs to produce useful outputs without splitting the pipeline into separate captioning and text-only stages unless there is a clear advantage.

## Decision
Use a **direct multimodal LLM flow with GPT-4o Vision**, combining extracted frames with retrieved case and guideline context in a single analysis step.

## Alternatives Considered
- **Image captioning + text RAG**: easier to isolate modalities, but adds an extra generation step and can lose image detail.
- **Text-only RAG**: simpler, but insufficient for image-driven clinical interpretation.

## Consequences
- Preserves more visual signal by sending frames directly to the multimodal model.
- Simplifies orchestration because the analysis pipeline remains one main reasoning step.
- Depends on a capable vision model and well-structured prompt construction.
- Makes retrieval quality and frame selection especially important, since both feed the same final inference stage.

## Notes
This strategy is already reflected in the current `/analyze-case` flow and README architecture diagram.