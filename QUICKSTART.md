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
- **documents.jsonl**: 26 case cards + 260 frame metadata (286 documenti totali)
- **labels.csv**: mapping case_id → diagnosis label
- **images/**: frame estratti da ogni caso (~10 frame per DICOM)

**Cartelle raw_data** (14 categorie diagnostiche):
- Normal (10 casi)
- Normal variations: septal hypertrophy, mitral valve prolapse, athlete heart, etc. (6 casi)
- Pathological: dilated cardiomyopathy, global LV dysfunction, inferoapical akinesia, etc. (10 casi)

### Rigenerare il dataset

Se aggiungi nuovi file DICOM o vuoi rigenerare:

```bash
./rebuild_dataset.sh
```

Questo cancella e ricrea `documents.jsonl` e le immagini.

## Struttura

- **Backend API**: FastAPI su porta 8000
- **Vectorstore**: Qdrant in-memory con auto-indexing
- **Dataset base**: 26 casi cardiologici (DICOM) processati automaticamente
- **Collection indicizzate**:
  - `cases`: 26 case_cards da `data/dataset_built/documents.jsonl` (generato da raw DICOM)
  - `guidelines`: chunk da 13 file guideline in `data/guidelines_txt/*.txt`

## API Endpoints

### POST /chat ⚠️ [DISABILITATO - Disponibile in sviluppi futuri]
Endpoint temporaneamente disabilitato. Attualmente il sistema è ottimizzato per l'analisi di casi specifici tramite `/analyze-case`. L'endpoint chat generico sarà riabilitato in future release per query esplorative.

**Endpoint attivo**: Usa `/analyze-case` per analisi multimodale di DICOM.

<details>
<summary>Specifica originale (per sviluppi futuri)</summary>

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

</details>

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
# Test /list-docs (endpoint attivo)
curl "http://localhost:8000/list-docs?rag_type=cases"

# Test /analyze-case (endpoint principale)
curl -X POST http://localhost:8000/analyze-case \
  -F "file=@data/raw_data/Normal/IM-0001-0032.dcm"
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
