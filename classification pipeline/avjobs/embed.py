"""Local sentence-transformer embeddings with chunked mean-pooling.

all-MiniLM-L6-v2 truncates at 256 word-pieces, so a long text embedded in one
shot loses its tail. Chunking and mean-pooling keeps the whole text in the
vector at negligible CPU cost.
"""

from __future__ import annotations

import hashlib

import numpy as np

from . import config as cfg


def chunk_words(text: str, size: int, overlap: int, max_chunks: int) -> list[str]:
    """Split into overlapping word windows."""
    words = text.split()
    if len(words) <= size:
        return [" ".join(words)]
    step = max(1, size - overlap)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)][:max_chunks]


def build_chunks(texts) -> tuple[list[str], list[int]]:
    """Flatten every text into chunks, tracking which text each belongs to."""
    all_chunks: list[str] = []
    owners: list[int] = []
    for doc_i, text in enumerate(texts):
        for chunk in chunk_words(text, cfg.CHUNK_WORDS, cfg.CHUNK_OVERLAP_WORDS,
                                 cfg.MAX_CHUNKS_PER_DOC):
            all_chunks.append(chunk)
            owners.append(doc_i)
    return all_chunks, owners


def _cache_key(texts) -> str:
    h = hashlib.sha1()
    h.update(cfg.EMBED_MODEL.encode())
    h.update(f"{cfg.CHUNK_WORDS}-{cfg.CHUNK_OVERLAP_WORDS}-{cfg.MAX_CHUNKS_PER_DOC}".encode())
    for text in texts:
        h.update(text.encode("utf-8", "ignore"))
    return h.hexdigest()[:16]


def embed_postings(texts, use_cache: bool = True) -> np.ndarray:
    """Return one L2-normalised vector per text (chunk mean-pooled)."""
    texts = list(texts)

    cfg.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = cfg.CACHE_DIR / f"emb_{_cache_key(texts)}.npy"
    if use_cache and cache_path.exists():
        print(f"  [embed] cache hit -> {cache_path.name}")
        return np.load(cache_path)

    from sentence_transformers import SentenceTransformer

    print(f"  [embed] loading {cfg.EMBED_MODEL} (local, CPU)")
    model = SentenceTransformer(cfg.EMBED_MODEL)

    chunks, owners = build_chunks(texts)
    print(f"  [embed] {len(texts)} postings -> {len(chunks)} chunks")

    chunk_vecs = model.encode(
        chunks,
        batch_size=cfg.EMBED_BATCH_SIZE,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    dim = chunk_vecs.shape[1]
    doc_vecs = np.zeros((len(texts), dim), dtype=np.float32)
    counts = np.zeros(len(texts), dtype=np.int32)
    np.add.at(doc_vecs, np.asarray(owners), chunk_vecs)
    np.add.at(counts, np.asarray(owners), 1)
    doc_vecs /= np.maximum(counts, 1)[:, None]

    # Re-normalise after pooling so cosine distance stays well-behaved.
    norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True)
    doc_vecs = doc_vecs / np.maximum(norms, 1e-9)

    if use_cache:
        np.save(cache_path, doc_vecs)
    return doc_vecs
