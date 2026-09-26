"""Central tunables. Edit here rather than hunting through the modules."""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_JSON = PROJECT_ROOT / "jobs-2026-09-03.json"
TEST_SET_JSON = PROJECT_ROOT / "test_set_postings.json"
REFERENCE_JSON = PROJECT_ROOT / "sonnet5_reference_answers.json"

OUTPUT_DIR = PROJECT_ROOT / "output_v3"
CACHE_DIR = PROJECT_ROOT / ".cache"

# --------------------------------------------------------------------------
# LLM normalisation
# --------------------------------------------------------------------------
# An OpenRouter model id. Must support structured outputs. Chosen over
# gpt-4o-mini on the 14 reference postings (output_model_check/): it matched
# Sonnet 5's av_relevant on 14/14 (gpt-4o-mini 8/14) at about the same cost.
# llm.py switches its reasoning off, and it takes no temperature (ignored).
LLM_MODEL = "openai/gpt-6-luna"
LLM_CACHE_DIR = CACHE_DIR / "llm"
LLM_TEMPERATURE = 0.0
# Model calls in flight at once. Each is still one posting; OpenRouter's limits for paid
# models are far above this. A full run drops from ~6 h (one at a time) to under an hour.
LLM_WORKERS = 10

# Output tokens per posting assumed by --dry-run (input tokens are counted
# exactly). gpt-6-luna averaged 744 on the 14 reference postings.
LLM_EST_OUTPUT_TOKENS = 750

# --------------------------------------------------------------------------
# Embedding
# --------------------------------------------------------------------------
EMBED_MODEL = "all-MiniLM-L6-v2"

# MiniLM truncates at 256 word-pieces (~180 words), so longer texts are
# chunked and the chunk vectors mean-pooled instead of silently truncated.
CHUNK_WORDS = 160
CHUNK_OVERLAP_WORDS = 32
MAX_CHUNKS_PER_DOC = 12
EMBED_BATCH_SIZE = 64

# --------------------------------------------------------------------------
# Clustering
# --------------------------------------------------------------------------
RANDOM_SEED = 42

# UMAP before HDBSCAN: on the raw 384-d vectors HDBSCAN degenerates on this
# dataset (one giant cluster, or >90% noise). See cluster.py.
UMAP_COMPONENTS = 5
UMAP_N_NEIGHBORS = 15
UMAP_MIN_DIST = 0.0         # 0.0 packs points tightly, which suits density clustering

MIN_CLUSTER_SIZE = 8
# Lower than min_cluster_size on purpose. HDBSCAN's default (min_samples ==
# min_cluster_size) is very conservative and pushes most postings to noise.
MIN_SAMPLES = 2
CLUSTER_SELECTION_METHOD = "eom"   # "eom" (fewer, larger) or "leaf" (more, finer)
CLUSTER_SELECTION_EPSILON = 0.0

# Grid tried by `--sweep` so you can see the size distribution before committing.
SWEEP_MIN_CLUSTER_SIZES = [5, 8, 10, 12, 15, 20]
SWEEP_MIN_SAMPLES = [2, 5]

TOP_TFIDF_TERMS = 15
EXAMPLE_TITLES_PER_CLUSTER = 5

# --------------------------------------------------------------------------
# Deduplication
# --------------------------------------------------------------------------
NEAR_DUP_THRESHOLD = 0.95   # cosine on word 1-3 gram TF-IDF, compared within company

# --------------------------------------------------------------------------
# Seniority
# --------------------------------------------------------------------------
# The values the model may return (ordered low -> high). Chosen to line up with
# sonnet5_reference_answers.json and v1, so the runs compare like with like.
SENIORITY_LABELS = [
    "Intern", "Graduate", "Entry", "Junior", "Mid", "Senior",
    "Staff", "Lead", "Principal", "Manager", "Senior Manager",
    "Director", "VP", "Executive", "Other",
]

# --------------------------------------------------------------------------
# Technical-leaning score (for validating the trap cases without hand labels)
# --------------------------------------------------------------------------
TECHNICAL_SEED_TERMS = [
    "perception", "planning", "prediction", "localization", "localisation",
    "slam", "lidar", "radar", "sensor", "calibration", "odometry",
    "autonomy", "autonomous", "self-driving", "driverless", "robotics",
    "motion planning", "control", "controls", "trajectory", "kinematics",
    "machine learning", "deep learning", "neural network", "computer vision",
    "reinforcement learning", "model training", "inference", "dataset",
    "simulation", "simulator", "software engineer", "c++", "python", "ros",
    "embedded", "firmware", "kernel", "linux", "distributed systems",
    "infrastructure", "pipeline", "api", "backend", "frontend", "fleet",
    "telemetry", "hardware", "electrical", "mechanical", "cad", "validation",
    "test", "algorithm", "optimization", "gpu", "cuda", "pytorch", "tensorflow",
]

CORPORATE_SEED_TERMS = [
    "accounting", "accounts payable", "payroll", "invoice", "audit", "gaap",
    "recruiting", "recruiter", "talent acquisition", "sourcing", "candidate",
    "human resources", "hr", "onboarding", "benefits administration",
    "legal", "counsel", "contract", "compliance", "litigation", "regulatory",
    "marketing", "brand", "campaign", "social media", "content", "copywriting",
    "sales", "customer", "account executive", "pipeline generation",
    "communications", "stakeholder", "executive", "roadmap", "program management",
    "project management", "coordination", "scheduling", "budget", "vendor",
    "facilities", "office management", "procurement", "logistics",
]
