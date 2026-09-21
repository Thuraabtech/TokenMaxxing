"""Build the FAISS index from app/data/sample_docs. Run from backend/:

    python -m app.data.ingest

Replace the sample_docs/ contents with your own corpus and re-run this any
time the source documents change.
"""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import settings

DATA_DIR = Path(__file__).resolve().parent
SAMPLE_DOCS_DIR = DATA_DIR / "sample_docs"


def load_documents() -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = []
    for path in sorted(SAMPLE_DOCS_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        for chunk in splitter.split_text(text):
            docs.append(Document(page_content=chunk, metadata={"source": path.name}))
    return docs


def main() -> None:
    docs = load_documents()
    if not docs:
        raise SystemExit(f"No .txt files found in {SAMPLE_DOCS_DIR}")

    embeddings = BedrockEmbeddings(model_id=settings.embedding_model_id, region_name=settings.aws_region)
    store = FAISS.from_documents(docs, embeddings)

    index_path = Path(settings.faiss_index_dir)
    if not index_path.is_absolute():
        index_path = DATA_DIR.parent.parent / settings.faiss_index_dir
    index_path.mkdir(parents=True, exist_ok=True)
    store.save_local(str(index_path))
    print(f"Indexed {len(docs)} chunks from {SAMPLE_DOCS_DIR} -> {index_path}")


if __name__ == "__main__":
    main()
