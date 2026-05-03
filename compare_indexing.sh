#!/bin/bash
# Comparison between the two indexing systems

echo "=== Indexing Systems Comparison ==="
echo ""
echo "✅ NEW: scripts/index_Qdrant.py (active)"
echo "   - Pattern singleton con auto-indexing"
echo "   - Indexes: 176 documents (16 case_cards + 160 frames)"
echo "   - Indexes: 9 guideline chunks"
echo "   - Used by: API, start.sh, multimodal_rag_openai.py"
echo ""
echo "❌ OLD: src/vectorstore_manager.py (deprecated)"
echo "   - Pattern singleton originale"
echo "   - Backup available: scripts/index_Qdrant.py.backup"
echo ""
echo "📝 Key difference:"
echo "   - Both index case_cards AND frames (176 docs)"
echo "   - index_Qdrant uses a cleaner architecture"
echo ""
