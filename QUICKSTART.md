# RAG Healthcare System - Quick Start

## Setup

1. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

2. **Install dependencies (reproducible)**:
  ```bash
  pip install -r requirements.lock
  ```

3. **Set the OpenAI API key**:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

4. **Start the system**:
   ```bash
   make start
   # or
   ./start.sh
   ```

   The startup script automatically:
   - Checks and activates the environment
   - Installs dependencies
   - **Builds the dataset from DICOM files** (if `documents.jsonl` does not exist)
   - Initializes and populates the vectorstore (auto-indexing)
   - **Starts FastAPI backend** on http://localhost:8000
   - **Starts Streamlit UI** on http://localhost:8501

## Streamlit UI

After startup, open **http://localhost:8501**

### Tab 1: 🔬 Analyze Case (PRIMARY)
Upload a DICOM file plus an optional clinical report for full multimodal analysis:
- Extracts ultrasound frames
- Retrieves similar cases through semantic RAG
- Generates an AI-assisted clinical response with GPT-4o vision
- Shows sources (case retrieval) and evaluation

### Tab 2: 📤 Upload DICOM
Upload and store a DICOM file without running immediate analysis.

### Tab 3: 📋 Manage Files
- List uploaded files in the system
- Delete specific files

### Bottom Actions
- 🔄 **Reset RAG Collections**: Soft reset (recreates all collections)
- 🗑️ **Clear Session**: Clears UI session state

## Base Dataset

On first startup, the script automatically runs:

```bash
python3 scripts/build_dataset.py
```

This processes DICOM files in `data/raw_data/` and generates:
- **documents.jsonl**: 26 case cards + 260 frame metadata (286 documents total)
- **labels.csv**: mapping case_id → diagnosis label
- **images/**: extracted frames from each case (~10 frames per DICOM)

**raw_data folders** (14 diagnostic categories):
- Normal (10 cases)
- Normal variants: septal hypertrophy, mitral valve prolapse, athlete heart, etc. (6 cases)
- Pathological: dilated cardiomyopathy, global LV dysfunction, inferoapical akinesia, etc. (10 cases)

### Rebuild the dataset

If you add new DICOM files or want to rebuild:

```bash
./rebuild_dataset.sh
```

This deletes and recreates `documents.jsonl` and the extracted images.

## Structure

- **Backend API**: FastAPI on port 8000
- **Vectorstore**: in-memory Qdrant with auto-indexing
- **Base dataset**: 26 cardiology DICOM cases processed automatically
- **Indexed collections**:
  - `cases`: 26 case cards from `data/dataset_built/documents.jsonl` (generated from raw DICOM)
  - `guidelines`: chunks from 13 guideline files in `data/guidelines_txt/*.txt`

## API Endpoints

### POST /analyze-case ✅ [PRIMARY]
Main endpoint: upload DICOM + optional report for complete multimodal analysis.

```bash
curl -X POST http://localhost:8000/analyze-case   -F "file=@/path/to/file.dcm"   -F "report_text=Optional clinical findings"
```

**Parameters**:
- `file`: DICOM file (required)
- `report_text`: clinical report text (optional)

**Response**:
```json
{
  "ok": true,
  "filename": "IM-0001-0032.dcm",
  "num_frames": 10,
  "frames_dir": "/path/to/extracted/frames",
  "analysis": {
    "answer": "Clinical analysis text from GPT-4o...",
    "sources": [
      {
        "type": "case",
        "id": "case_123",
        "score": 0.87,
        "snippet": "...",
        "metadata": {...}
      }
    ],
    "evaluation": null
  }
}
```

### Other available endpoints
- `POST /upload-doc`
- `GET /list-docs`
- `POST /delete-doc`
- `POST /flush-rag`
- `GET /metrics` — Prometheus metrics (HTTP + RAG/DICOM counters)

```bash
curl -s http://localhost:8000/metrics | head
```

With Docker, enable the monitoring stack (`make monitoring-up`) for Prometheus (9090) and Grafana (3000). See [DOCKER.md](DOCKER.md#-monitoring-stack-optional).

## Quick test

```bash
# Test /analyze-case (main endpoint) with a local DICOM file
curl -X POST http://localhost:8000/analyze-case   -F "file=@data/raw_data/Normal/IM-0001-0032.dcm"

# With optional report
curl -X POST http://localhost:8000/analyze-case   -F "file=@data/raw_data/Normal/IM-0001-0032.dcm"   -F "report_text=Normal cardiac function"

# Test /list-docs to view uploaded files
curl "http://localhost:8000/list-docs?rag_type=cases"

# Reset RAG collections
curl -X POST http://localhost:8000/flush-rag
```

## Interactive docs

Open http://localhost:8000/docs for Swagger UI with all endpoints.

## Notes

- **documents.jsonl**: if missing, the `cases` collection is empty (only guidelines are indexed)
- **Auto-indexing**: the vectorstore is populated automatically at startup
- **In-memory**: data is lost on restart (you can switch to remote Qdrant in `vectorstore_manager.py`)

## Switch to remote Qdrant

1. Start Qdrant server:
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

2. Edit `src/vectorstore_manager.py`:
   ```python
   vectorstore = QdrantVectorstore(host="localhost", port=6333)
   ```
