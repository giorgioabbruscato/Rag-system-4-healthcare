from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
      # API
      api_host: str = "0.0.0.0"
      api_port: int = Field(8000, ge=1024, le=65535)
      allowed_origins: List[str] = ["http://localhost:8501"]
      debug: bool = False

      # OpenAI
      openai_api_key: str = ""
      openai_model: str = "gpt-4o"

      # Embeddings
      embedding_model: str = "all-MiniLM-L6-v2"
      embedding_dim: int = 384
      vector_name: str = "text_embedding"

      # RAG
      topk_cases: int = Field(5, ge=1)
      topk_guidelines: int = Field(4, ge=1)
      chunk_size: int = 800
      chunk_overlap: int = 150
      frames_per_case: int = 3
      max_query_frames: int = 12
      max_similar_frames_total: int = 12
      knn_min_score_threshold: float = 2.5

      # Qdrant
      qdrant_host: str = "localhost"
      qdrant_port: int = 6333
      qdrant_in_memory: bool = True

      # Paths
      data_dir: str = "data"
      raw_data_dir: str = "data/raw_data"
      dataset_dir: str = "data/dataset_built"
      guidelines_dir: str = "data/guidelines_txt"

      # Upload limits
      max_upload_size_mb: int = Field(100, gt=0)

      model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()