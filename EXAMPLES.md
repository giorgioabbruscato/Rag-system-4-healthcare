# Practical Examples - RAG Healthcare

> ⚠️ **Note**: Examples using `/chat` are currently disabled. The system is optimized for multimodal analysis through `/analyze-case`. The `/chat` endpoint will be re-enabled in future development for generic exploratory queries.

## 1. Start the system

```bash
# Terminal 1: Start backend
export OPENAI_API_KEY="sk-..."
./start.sh

# Expected output:
# [1/5] Checking Python environment... ✓
# [2/5] Checking dependencies... ✓
# [3/5] Building dataset from DICOM files... (first run)
#       ✓ Dataset already exists (otherwise)
# [4/5] Checking environment variables... ✓
# [5/5] Initializing vectorstore...
#       [VectorstoreManager] Indexed 26 cases. ✓
#       [VectorstoreManager] Indexed 13 guideline files. ✓
# === Starting FastAPI Backend ===
# INFO: Uvicorn running on http://0.0.0.0:8000
```

## 2. RAG Query - Similar Cases [DISABLED - Future Development]

<details>
<summary>⚠️ Example for future development (endpoint currently disabled)</summary>

```bash
# Search similar cases for dilated cardiomyopathy
curl -X POST http://localhost:8000/chat   -H "Content-Type: application/json"   -d '{
    "question": "What are the echocardiographic findings in dilated cardiomyopathy?",
    "model": "gpt-4o",
    "rag_type": "cases",
    "evaluate": false
  }' | jq .

# Response:
# {
#   "answer": "[RAG stub - cases]\nQuery: ...\nRetrieved 5 sources...",
#   "sources": [
#     {
#       "type": "case",
#       "id": "a53a50ad3d3e",
#       "score": 0.789,
#       "snippet": "Ultrasound multiframe study. View: Unknown...",
#       "metadata": {
#         "diagnosis_label_pretty": "Dilated cardiomyopathy with global dysfunction",
#         "num_frames": 111,
#         "motion_energy": 0.0234,
#         ...
#       }
#     },
#     ...
#   ],
#   "session_id": "session-auto"
# }
```

</details>

## 3. RAG Query - Guidelines [DISABLED - Future Development]

<details>
<summary>⚠️ Example for future development (endpoint currently disabled)</summary>

```bash
# Search guideline content
curl -X POST http://localhost:8000/chat   -H "Content-Type: application/json"   -d '{
    "question": "What is the normal echo appearance of the left ventricle?",
    "model": "gpt-4o",
    "rag_type": "guidelines"
  }' | jq .

# Retrieves relevant chunks from:
# - normal_echo_background.txt
# - dilated_cardiomyopathy_background.txt (for contrast)
```

</details>

## 4. RAG Query - Hybrid (Cases + Guidelines) [DISABLED - Future Development]

<details>
<summary>⚠️ Example for future development (endpoint currently disabled)</summary>

```bash
curl -X POST http://localhost:8000/chat   -H "Content-Type: application/json"   -d '{
    "question": "Compare normal vs pathological septal motion",
    "model": "gpt-4o",
    "rag_type": "hybrid"
  }' | jq .

# Retrieves:
# - Normal and pathological cases from the cases vectorstore
# - Theoretical background from the guidelines vectorstore
```

</details>

## 5. Upload DICOM and extract frames

```bash
# Upload new DICOM case
curl -X POST http://localhost:8000/upload-doc   -F "file=@data/raw_data/Normal/IM-0001-0032.dcm"   -F "model=gpt-4o"   -F "rag_type=multimodal" | jq .

# Response:
# {
#   "ok": true,
#   "file_id": "...",
#   "frames_saved": 12,
#   "output_folder": "data/current_case_frames"
# }
```

## 6. List uploaded documents

```bash
curl "http://localhost:8000/list-docs?rag_type=cases" | jq .

# Response:
# {
#   "files": [
#     {
#       "file_id": "current_case_123",
#       "uploaded_at": "2026-01-16T22:30:00",
#       "frames": 12
#     }
#   ]
# }
```

## 7. Delete a document

```bash
curl -X POST http://localhost:8000/delete-doc   -H "Content-Type: application/json"   -d '{"file_id": "current_case_123"}' | jq .

# Response:
# {
#   "ok": true,
#   "deleted": "current_case_123"
# }
```

## 8. Manual vectorstore test

```bash
# Direct retrieval test
python3 src/vectorstore_manager.py

# Output:
# === Vectorstore Manager Test ===
# [VectorstoreManager] Initializing Qdrant in-memory...
# [VectorstoreManager] Auto-indexing collections...
# [VectorstoreManager] ✓ Indexed 26 cases.
# [VectorstoreManager] ✓ Indexed 13 guideline files.
#
# Test search: 'dilated cardiomyopathy with reduced ejection fraction'
# Found 3 results:
#   1. 36ff771bde40 - Normal
#      Ultrasound multiframe study. View: Unknown...
#   2. 02667f14217e - Normal
#      Ultrasound multiframe study. View: Unknown...
#   3. a53a50ad3d3e - Normal
#      Ultrasound multiframe study. View: Unknown...
```

## 9. Rebuild dataset

```bash
# Add new DICOM files to data/raw_data/
cp /path/to/new_study.dcm data/raw_data/Normal/

# Rebuild dataset
./rebuild_dataset.sh

# Output:
# === Rebuild Dataset ===
# Dataset already exists. This will DELETE and REBUILD it.
# Continue? (y/N): y
# Removing old dataset...
# Building dataset from DICOM files...
# ✓ Dataset built successfully!
#   Total documents: 297  (if you add 1 case)
#   Case cards: 27
#   Frames: 270

# Restart backend for re-indexing
./start.sh
```

## 10. Swagger UI - Interactive docs

```bash
# Open browser:
open http://localhost:8000/docs

# Graphical interface to:
# - Test all endpoints
# - View request/response schemas
# - Run requests directly from the browser
```

## 11. Health check

```bash
# Verify backend is active
curl http://localhost:8000/docs | head -5

# Output: Swagger page HTML (status 200)
```

## 12. Standalone multimodal script

```bash
# Test multimodal RAG pipeline (outside backend)
python3 scripts/multimodal_rag_openai.py

# Interactive input:
# Paste the clinical report (finish with an empty line):
# > Patient presents with dyspnea on exertion.
# > Echo shows dilated LV with reduced EF.
# >
# Optional: folder containing CURRENT exam frames (press Enter to skip):
# > data/current_case_frames
#
# --- MODEL OUTPUT ---
# (GPT-4o response with diagnosis + differential + evidence + sources)
```

## 13. Analyze generated dataset

```bash
# Count documents by type
jq -r '.metadata.document_type' data/dataset_built/documents.jsonl | sort | uniq -c

# Output:
#  26 case_card
# 260 frame

# Count cases by diagnosis
jq -r '.metadata.diagnosis_label_pretty' data/dataset_built/documents.jsonl |   grep -v null | sort | uniq -c

# Output:
# 100 Normal
#  10 Normal with septal hypertrophy
#  10 Normal function mitral valve prolapse
#  10 Dilated cardiomyopathy with global dysfunction
#  40 Inferoapical septal akinesia
# ... (14 categories total)
#  40 Inferoapical septal akinesia
```

## 14. Extract frames from a single DICOM

```bash
# Extract 12 uniformly spaced frames
python3 scripts/dicom_to_frames_current.py   --dicom data/raw_data/Normal/IM-0001-0032.dcm   --out data/test_frames   --n 12

# Output:
# DICOM: data/raw_data/Normal/IM-0001-0032.dcm
# Frames in DICOM: 143 | Saved: 12
# View: None | Stage: None | FPS: 63
# Output folder: data/test_frames
```

## 15. Debugging

```bash
# Check backend logs
tail -f uvicorn_log.txt  # (if output is redirected)

# Check in-memory vectorstore
python3 -c "
from src.vectorstore_manager import get_vectorstore
vs = get_vectorstore()
print('Vectorstore ready')
"

# Check indexed documents
wc -l data/dataset_built/documents.jsonl

# Check extracted images
find data/dataset_built/images -name "*.png" | wc -l

# Check dependencies
pip list | grep -E "qdrant|datapizza|sentence"
```

## 16. Performance tips

```bash
# Lower memory usage: reduce number of extracted frames
# In scripts/build_dataset.py, export_representative_frames:
export_representative_frames(ds, case_id, n=5)  # instead of 10

# Speed up indexing: reduce max_frames for feature extraction
# In scripts/build_dataset.py, compute_simple_video_features:
compute_simple_video_features(ds, max_frames=32)  # instead of 64

# Switch to persistent Qdrant (avoid re-indexing on each restart)
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
# Then update vectorstore_manager.py to use host="localhost"
```

## 17. Common errors

### Error: "No module named 'sentence_transformers'"
```bash
# Fix: activate environment and reinstall
source .venv/bin/activate
pip install -r requirements.txt
```

### Error: "documents.jsonl not found"
```bash
# Fix: build dataset
python3 scripts/build_dataset.py
```

### Error: "OPENAI_API_KEY not set"
```bash
# Fix: set variable
export OPENAI_API_KEY="sk-..."
# Verify
echo $OPENAI_API_KEY
```

### Error: "Port 8000 already in use"
```bash
# Inspect the process using port 8000 and stop it manually
lsof -nP -iTCP:8000 -sTCP:LISTEN
# Or use another port
uvicorn api.main:app --port 8001
```
