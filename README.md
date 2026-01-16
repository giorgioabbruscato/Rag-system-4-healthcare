# RAG System for Healthcare

Sistema RAG (Retrieval-Augmented Generation) multimodale per supporto decisionale clinico in cardiologia. Combina analisi di immagini ecografiche DICOM, retrieval semantico di casi simili e linee guida per generare risposte diagnostiche assistite da AI.

## ⚠️ Privacy & Anonymization

**All patient data has been fully anonymized** in compliance with GDPR and HIPAA regulations.

- ✅ All DICOM metadata is anonymized (names, dates, IDs removed)
- ✅ Only non-identifiable clinical/technical data is preserved
- ✅ Safe for public repository publication

📖 See [ANONYMIZATION.md](ANONYMIZATION.md) for details.

## Quick Start

```bash
# 1. Setup ambiente
source .venv/bin/activate

# 2. Imposta API key OpenAI
export OPENAI_API_KEY="sk-..."

# 3. Avvia il sistema (auto-build dataset + auto-indexing)
./start.sh
```

Il backend sarà disponibile su **http://localhost:8000** (docs: http://localhost:8000/docs)

📖 **Guida completa API**: vedi [QUICKSTART.md](QUICKSTART.md)

## Architettura

### Dataset Base (Auto-generato)
- **16 casi cardiologici** (file DICOM) → 176 documenti indicizzati
  - Normal (10), Normal with septal hypertrophy (1)
  - Dilated cardiomyopathy (1), Inferoapical akinesia (4)
- **Frame extraction**: 10 frame/caso + metadata (view, fps, motion features)
- **Auto-indexing**: vectorstore Qdrant popolato automaticamente all'avvio

### Pipeline
1. **Build Dataset**: `scripts/build_dataset.py` processa DICOM → `documents.jsonl`
2. **Vectorstore Manager**: auto-indexing con SentenceTransformer (all-MiniLM-L6-v2)
3. **RAG Service**: retrieval semantico + prompt augmentation
4. **FastAPI Backend**: REST API per chat, upload DICOM, gestione documenti

## Comandi Utili

```bash
# Rigenerare dataset (se aggiungi DICOM in data/raw_data/)
./rebuild_dataset.sh

# Test manuale vectorstore + indexing
python3 src/vectorstore_manager.py

# Test API endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is dilated cardiomyopathy?","model":"gpt-4o","rag_type":"cases"}'
```

## Dettagli Tecnici

- **Embeddings**: SentenceTransformer all-MiniLM-L6-v2 (384 dim, locale, no API)
- **Vectorstore**: Qdrant in-memory (16 cases + 9 guideline chunks)
- **LLM**: OpenAI GPT-4o con vision (multimodale)
- **DICOM**: pydicom + PIL per frame extraction + metadata
- **Backend**: FastAPI + Pydantic + CORS

## Struttura

```
├── api/main.py                    # FastAPI app
├── src/vectorstore_manager.py     # Singleton Qdrant + auto-indexing
├── scripts/
│   ├── build_dataset.py           # DICOM → documents.jsonl
│   └── multimodal_rag_openai.py   # Pipeline RAG multimodale
├── data/
│   ├── raw_data/                  # DICOM originali (16 file)
│   ├── dataset_built/             # Auto-generato (documents.jsonl + images/)
│   └── guidelines_txt/            # Linee guida (3 file .txt)
├── start.sh                       # Avvio completo
└── rebuild_dataset.sh             # Rigenera dataset
```

## Requisiti

- Python 3.9+
- OpenAI API key
- ~2GB RAM (embeddings + vectorstore in-memory)

## Privacy Notice

⚠️ **Original DICOM files are NOT included** in this repository.

Only the anonymized derived dataset is provided. All patient-identifiable information has been removed in compliance with privacy regulations.

To verify anonymization:
```bash
python3 scripts/verify_anonymization.py
```