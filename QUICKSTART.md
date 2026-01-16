# RAG Healthcare System - Quick Start

## Setup

1. **Attiva l'ambiente virtuale**:
   ```bash
   source .venv/bin/activate
   ```

2. **Imposta la chiave API OpenAI**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

3. **Avvia il sistema**:
   ```bash
   ./start.sh
   ```
   
   Lo script automaticamente:
   - Verifica e attiva l'ambiente
   - Installa dipendenze
   - **Genera dataset da file DICOM** (se non esiste `documents.jsonl`)
   - Inizializza e popola il vectorstore (auto-indexing)
   - Avvia il backend FastAPI su http://localhost:8000

## Dataset Base

Al primo avvio, lo script esegue automaticamente:

```bash
python3 scripts/build_dataset.py
```

Questo processa i file DICOM in `data/raw_data/` e genera:
- **documents.jsonl**: 16 case cards + 160 frame metadata (176 documenti totali)
- **labels.csv**: mapping case_id → diagnosis label
- **images/**: frame estratti da ogni caso (10 frame per DICOM)

**Cartelle raw_data**:
- Normal (10 casi)
- Normal_with_septal_hypertrophy (1 caso)
- dilated_cardiomyopathy_with_global_dysfunction (1 caso)
- inferoapical_septal_akinesia (4 casi)

### Rigenerare il dataset

Se aggiungi nuovi file DICOM o vuoi rigenerare:

```bash
./rebuild_dataset.sh
```

Questo cancella e ricrea `documents.jsonl` e le immagini.

## Struttura

- **Backend API**: FastAPI su porta 8000
- **Vectorstore**: Qdrant in-memory con auto-indexing
- **Dataset base**: 16 casi cardiologici (DICOM) processati automaticamente
- **Collection indicizzate**:
  - `cases`: 16 case_cards da `data/dataset_built/documents.jsonl` (generato da raw DICOM)
  - `guidelines`: 9 chunk da 3 file guideline in `data/guidelines_txt/*.txt`

## API Endpoints

### POST /chat
Query RAG con retrieval da cases/guidelines.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are signs of dilated cardiomyopathy?",
    "model": "gpt-4o",
    "rag_type": "cases",
    "evaluate": false
  }'
```

**Parametri**:
- `question`: domanda clinica
- `model`: modello OpenAI (es. "gpt-4o")
- `rag_type`: "cases" | "guidelines" | "hybrid" | "multimodal"
- `evaluate`: bool (opzionale, per metriche)
- `session_id`: str (opzionale)

**Response**:
```json
{
  "answer": "...",
  "sources": [{"type": "case", "id": "...", "score": 0.85, "snippet": "...", "metadata": {...}}],
  "session_id": "...",
  "evaluation": null
}
```

### POST /upload-doc
Upload file DICOM ed estrazione frame.

```bash
curl -X POST http://localhost:8000/upload-doc \
  -F "file=@/path/to/file.dcm" \
  -F "model=gpt-4o" \
  -F "rag_type=multimodal"
```

### GET /list-docs
Lista file caricati nel sistema.

```bash
curl "http://localhost:8000/list-docs?rag_type=cases"
```

### POST /delete-doc
Rimuove un documento caricato.

```bash
curl -X POST http://localhost:8000/delete-doc \
  -H "Content-Type: application/json" \
  -d '{"file_id": "..."}'
```

### POST /flush-rag
Reset del sistema (soft).

```bash
curl -X POST http://localhost:8000/flush-rag \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Test rapido

```bash
# Test /chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"test","model":"gpt-4o","rag_type":"guidelines"}'
```

## Docs interattive

Apri http://localhost:8000/docs per Swagger UI.

## Note

- **documents.jsonl**: se manca, la collection `cases` sarà vuota (solo guidelines saranno indicizzate)
- **Auto-indexing**: al primo avvio il vectorstore viene popolato automaticamente
- **In-memory**: i dati sono persi al restart (puoi passare a Qdrant remoto modificando `vectorstore_manager.py`)

## Passare a Qdrant remoto

1. Avvia Qdrant server:
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

2. Modifica `src/vectorstore_manager.py`:
   ```python
   vectorstore = QdrantVectorstore(host="localhost", port=6333)
   ```
