# RAG Healthcare System - Implementation Summary

## ✅ Implemented

### 1. Dataset Auto-indexing
- **Script**: `scripts/build_dataset.py`
- **Input**: 26 DICOM files in `data/raw_data/` (14 diagnostic categories)
- **Output**:
  - `data/dataset_built/documents.jsonl` (286 documents)
  - `data/dataset_built/labels.csv` (27 mapped cases → diagnosis)
  - `data/dataset_built/images/` (260 extracted PNG frames, ~10/case)
- **Execution**: automatic at first startup via `start.sh`, or manual via `./rebuild_dataset.sh`

### 2. Vectorstore Manager (Singleton)
- **File**: `src/vectorstore_manager.py`
- **Features**:
  - In-memory Qdrant (configurable for remote server)
  - Auto-indexing on first use
  - Local embedding model: SentenceTransformer `all-MiniLM-L6-v2` (384 dim)
  - Collections:
    - `cases`: 26 case cards (metadata + extracted features)
    - `guidelines`: chunks from 13 guideline files
  - Deterministic UUIDs for document IDs
  - Error handling and logging

### 3. FastAPI Backend
- **File**: `api/main.py`
- **Active endpoints**:
  - `POST /analyze-case`: multimodal case analysis
  - `POST /upload-doc`: DICOM upload and frame extraction
  - `GET /list-docs`: list uploaded documents
  - `POST /delete-doc`: remove document
  - `POST /flush-rag`: soft system reset
- **Disabled endpoint**:
  - `POST /chat`: currently commented out in code
- **CORS**: enabled for local development
- **Docs**: Swagger UI at http://localhost:8000/docs

### 4. RAG Service
- **File**: `api/services/rag_service.py`
- **Capabilities**:
  - Semantic retrieval from vectorstore
  - Support for `rag_type`: cases, guidelines, hybrid
  - Returns answer + sources with metadata
  - Prepared for multimodal integration

### 5. Startup script
- **File**: `start.sh` (executable)
- **Flow**:
  1. Verify/create virtual environment
  2. Install dependencies from `requirements.txt`
  3. **Build dataset from DICOM** (if missing)
  4. Check `OPENAI_API_KEY`
  5. Initialize vectorstore (auto-indexing)
  6. Start FastAPI backend (`uvicorn`, hot reload)

### 6. Documentation
- **README.md**: architecture overview + quick start
- **QUICKSTART.md**: detailed API guide with curl examples
- **rebuild_dataset.sh**: script to rebuild dataset

## 📊 Indexed Data

### Cases (26 documents)
- **Normal**: 10 cases
- **Normal with septal hypertrophy**: 1 case
- **Normal function mitral valve prolapse**: 1 case
- **Normal function septal hypertrophy athlete heart**: 1 case
- **Normal function septal hypertrophy in aortic stenosis**: 1 case
- **Normal function severe septal hypertrophy**: 1 case
- **Normal tendinous cord function in apical region**: 1 case
- **Dilated cardiomyopathy with global dysfunction**: 1 case
- **Global left ventricular dysfunction**: 1 case
- **Global left ventricular dysfunction and apical akinesia**: 1 case
- **Inferoapical septal akinesia**: 4 cases
- **Left ventricular apical inferior septal aneurysm**: 1 case
- **Left ventricular dilatation with apical dyskinesia**: 1 case
- **Left ventricular dysfunction with apical akinesia and apical thrombosis**: 1 case

### Guidelines (13 files)
- `dilated_cardiomyopathy_background.txt`
- `global_left_ventricular_dysfunction.txt`
- `global_left_ventricular_dysfunction_and_apical_akinesia.txt`
- `inferoapical_akinesia_background.txt`
- `Left_ventricular_apical_inferior_septal_aneurysm.txt`
- `Left_ventricular_dilatation_with_apical_dyskinesia.txt`
- `left_ventricular_dysfunction_with_apical_akinesia_and_apical_thrombosis.txt`
- `normal_echo_background.txt`
- `normal_function_mitral_valve_prolapse.txt`
- `normal_function_septal_hypertrophy_athlete_heart.txt`
- `normal_function_septal_hypertrophy_in_aortic_stenosis.txt`
- `normal_function_severe_septal_hypertrophy.txt`
- `normal_tendinous_cord_function_in_apical_region.txt`

### Metadata extracted from DICOM
- View, stage, FPS, effective duration, heart rate
- Frame count, dimensions, photometric interpretation
- **Computed features**:
  - `mean_intensity`: normalized mean intensity
  - `motion_energy`: motion energy (difference between consecutive frames)
  - `motion_std`: motion standard deviation

## 🚀 How to use

### Quick start
```bash
export OPENAI_API_KEY="sk-..."
./start.sh
```

### API test
```bash
# RAG query on cases (endpoint currently disabled in api/main.py)
curl -X POST http://localhost:8000/chat   -H "Content-Type: application/json"   -d '{
    "question": "What are the characteristics of dilated cardiomyopathy?",
    "model": "gpt-4o",
    "rag_type": "cases",
    "evaluate": false
  }'

# Response includes:
# - answer: generated text (stub)
# - sources: array with retrieved case/guideline documents
# - session_id: for conversations
```

### Rebuild dataset
```bash
# If you add new DICOM files in data/raw_data/
./rebuild_dataset.sh
# Then restart backend for re-indexing
```

## 🔧 Configuration

### Switch to remote Qdrant
1. Start Qdrant server:
   ```bash
   docker run -d -p 6333:6333 qdrant/qdrant
   ```

2. Edit `src/vectorstore_manager.py` at line 27:
   ```python
   _vectorstore = QdrantVectorstore(host="localhost", port=6333)
   ```

3. Restart backend

### Environment variables
- `OPENAI_API_KEY`: required for LLM
- `QDRANT_HOST`: Qdrant server host (default: localhost)
- `QDRANT_PORT`: Qdrant port (default: 6333)
- `USE_REMOTE_QDRANT`: `"true"` to use a remote server (plannable)

## 📁 Full structure

```
Rag-system-4-healthcare/
├── api/
│   ├── main.py                         # FastAPI app (CORS, endpoints)
│   └── services/
│       ├── doc_service.py              # DICOM upload, list/delete docs
│       └── rag_service.py              # RAG query logic + retrieval
├── app/
│   └── streamlit_app.py                # Frontend (WIP)
├── data/
│   ├── raw_data/                       # Original DICOM files (INPUT)
│   │   ├── Normal/                     # 10 .dcm files
│   │   ├── Normal_with_septal_hypertrophy/  # 1 file
│   │   ├── dilated_cardiomyopathy_with_global_dysfunction/  # 1 file
│   │   ├── global_left_ventricular_dysfunction/  # 1 file
│   │   ├── global_left_ventricular_dysfunction_and_apical_akinesia/  # 1 file
│   │   ├── inferoapical_septal_akinesia/    # 4 files
│   │   ├── Left_ventricular_apical_inferior_septal_aneurysm/  # 1 file
│   │   ├── Left_ventricular_dilatation_with_apical_dyskinesia/  # 1 file
│   │   ├── left_ventricular_dysfunction_with_apical_akinesia_and_apical_thrombosis/  # 1 file
│   │   ├── normal_function_mitral_valve_prolapse/  # 1 file
│   │   ├── normal_function_septal_hypertrophy_athlete_heart/  # 1 file
│   │   ├── normal_function_septal_hypertrophy_in_aortic_stenosis/  # 1 file
│   │   ├── normal_function_severe_septal_hypertrophy/  # 1 file
│   │   └── normal_tendinous_cord_function_in_apical_region/  # 1 file
│   ├── dataset_built/                  # AUTO-GENERATED
│   │   ├── documents.jsonl             # 286 documents (26 cases + 260 frames)
│   │   ├── labels.csv                  # Case ID → label mapping (27 rows)
│   │   └── images/                     # Extracted frames (~10 per case)
│   │       ├── <case_id_1>/
│   │       │   ├── frame_1.png ... frame_10.png
│   │       └── ...
│   └── guidelines_txt/                 # Guidelines (INPUT)
│       ├── dilated_cardiomyopathy_background.txt
│       ├── global_left_ventricular_dysfunction.txt
│       ├── global_left_ventricular_dysfunction_and_apical_akinesia.txt
│       ├── inferoapical_akinesia_background.txt
│       ├── Left_ventricular_apical_inferior_septal_aneurysm.txt
│       ├── Left_ventricular_dilatation_with_apical_dyskinesia.txt
│       ├── left_ventricular_dysfunction_with_apical_akinesia_and_apical_thrombosis.txt
│       ├── normal_echo_background.txt
│       ├── normal_function_mitral_valve_prolapse.txt
│       ├── normal_function_septal_hypertrophy_athlete_heart.txt
│       ├── normal_function_septal_hypertrophy_in_aortic_stenosis.txt
│       ├── normal_function_severe_septal_hypertrophy.txt
│       └── normal_tendinous_cord_function_in_apical_region.txt
├── scripts/
│   ├── build_dataset.py                # DICOM → documents.jsonl (full pipeline)
│   ├── dicom_to_frames_current.py      # Single-case frame extraction
│   ├── multimodal_rag_openai.py        # Multimodal RAG pipeline
│   ├── index_Qdrant.py                 # Manual indexing (legacy, unused)
│   ├── index_guidelines.py             # Manual guideline indexing (legacy)
│   ├── query_retrieval.py              # Retrieval test (legacy)
│   └── eval_hitk_mrr.py                # Evaluation metrics (WIP)
├── src/
│   ├── __init__.py
│   └── vectorstore_manager.py          # ⭐ Singleton Qdrant + auto-indexing
├── .venv/                              # Python virtual environment
├── requirements.txt                    # Dependencies
├── start.sh                            # ⭐ Full startup script (executable)
├── rebuild_dataset.sh                  # ⭐ Rebuild dataset (executable)
├── README.md                           # Project overview
├── QUICKSTART.md                       # API guide + examples
└── LICENSE
```

## 🔄 Full workflow

```
[DICOM files in raw_data/]
         ↓
    build_dataset.py
         ↓
    documents.jsonl (286 docs) + images/ (260 frames)
         ↓
    vectorstore_manager.py (auto-indexing)
         ↓
    Qdrant collections (26 cases + 13 guidelines)
         ↓
     rag_service.py (retrieval)
         ↓
    FastAPI /analyze-case endpoint
         ↓
    [Response with analysis + retrieved sources]
 ```

## 🎯 Next steps

### High priority
- [ ] Integrate `multimodal_rag_openai.py` fully into `rag_service.py`
- [ ] Implement current-case frame management in `upload-doc`
- [ ] Add real OpenAI GPT-4o call (currently stubbed)

### Medium priority
- [ ] Implement memory-enabled sessions/conversations
- [ ] Add evaluation metrics (ragas)
- [ ] Complete Streamlit frontend
- [ ] Structured logging (JSON)

### Low priority
- [ ] Move to persistent Qdrant (Docker)
- [ ] Response caching
- [ ] API rate limiting
- [ ] Authentication/authorization

## 🐛 Known issues

1. **Case semantic search**: currently retrieves "Normal" cases even for pathology queries (embeddings are too generic for metadata; prompt engineering or fine-tuning is needed)
2. **OpenAI call**: still a stub, real call not integrated
3. **Session management**: not implemented (`session_id` is ignored)
4. **Evaluation**: metrics are not connected

## 💡 Technical notes

- **Deterministic UUIDs**: `uuid.uuid5` with DNS namespace is used to generate reproducible IDs from case_id/guideline_id
- **DenseEmbedding**: datapizza requires `DenseEmbedding(name, vector)` objects, not dict/list
- **Chunk API**: `QdrantVectorstore.add()` accepts `Chunk` objects, not separate parameters
- **Search results**: returns a list of `Chunk`, not objects with `.score` (`score` is internal)
- **Embedding dimensions**: 384 for `all-MiniLM-L6-v2` (not 1536 like OpenAI)

## 📞 Support

For issues or questions:
1. Check backend logs (uvicorn stdout)
2. Verify that `documents.jsonl` exists and is not empty
3. Test vectorstore manually: `python3 src/vectorstore_manager.py`
4. Verify that `OPENAI_API_KEY` is set
