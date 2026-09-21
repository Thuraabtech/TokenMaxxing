from pathlib import Path

from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS

from app.config import settings

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_vectorstore = None


def _embeddings():
    return BedrockEmbeddings(model_id=settings.embedding_model_id, region_name=settings.aws_region)


def _index_path() -> Path:
    path = Path(settings.faiss_index_dir)
    return path if path.is_absolute() else BACKEND_ROOT / path


def load_index() -> FAISS:
    global _vectorstore
    if _vectorstore is None:
        index_path = _index_path()
        if not index_path.exists():
            raise FileNotFoundError(
                f"No FAISS index at {index_path}. Run `python -m app.data.ingest` from backend/ first."
            )
        _vectorstore = FAISS.load_local(
            str(index_path), _embeddings(), allow_dangerous_deserialization=True
        )
    return _vectorstore


def retrieve(query: str, k: int | None = None) -> list[dict]:
    store = load_index()
    k = k or settings.retrieval_top_k
    docs_and_scores = store.similarity_search_with_score(query, k=k)
    return [
        {
            "text": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "score": round(float(score), 4),
        }
        for doc, score in docs_and_scores
    ]
