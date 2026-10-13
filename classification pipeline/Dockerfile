# LLM normalisation + embedding + UMAP/HDBSCAN clustering (run_pipeline_v2.py)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false \
    HF_HOME=/opt/hf \
    NUMBA_CACHE_DIR=/tmp/numba

WORKDIR /app

# CPU-only PyTorch first: avoids pulling the multi-GB CUDA build
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model into the image so runs need no Hugging Face download
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY avjobs/ avjobs/
COPY run_pipeline_v2.py schema.mysql.sql ./

# input/  -> data-collection/deliverables (read-only, mounted)
# output/ -> results (mounted);  .cache/ -> LLM reply + embedding cache (volume)
ENTRYPOINT ["python", "run_pipeline_v2.py"]
CMD ["--help"]
