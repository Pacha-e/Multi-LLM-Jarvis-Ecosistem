"""J.A.R.V.I.S. — RAG (Retrieval-Augmented Generation) Module

Indexes personal knowledge bases and retrieves relevant context
before each LLM call.

Supported sources:
  1. Obsidian vault (Markdown notes)
  2. Local directories (any .txt/.md files)
  3. PDF documents (requires pypdf)
  4. Web URLs (future)

Architecture:
  Files → chunked → embedded (sentence-transformers) → ChromaDB
  Query → embed → cosine similarity search → top-k chunks → context

Setup:
  pip install chromadb sentence-transformers

Usage:
    rag = JarvisRAG()
    rag.index_directory("/path/to/obsidian/vault")
    context = rag.retrieve("qué notas tengo sobre python")
    # context injected into system prompt before LLM call
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE = 500        # chars per chunk
CHUNK_OVERLAP = 100     # overlap between chunks
TOP_K = 4               # number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.3  # min similarity to include


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks


def _clean_markdown(text: str) -> str:
    """Remove markdown syntax for cleaner embedding."""
    text = re.sub(r"#{1,6}\s+", "", text)       # headers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text) # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)      # italic
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text) # code
    text = re.sub(r"\[\[(.+?)\]\]", r"\1", text)  # wiki links
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)  # markdown links
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)  # bullets
    return text.strip()


class JarvisRAG:
    """
    Personal knowledge base RAG for J.A.R.V.I.S.

    Two operation modes:
      1. ChromaDB (persistent, fast) — preferred
      2. In-memory TF-IDF (fallback, no extra deps)
    """

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or os.path.join(
            os.path.dirname(__file__), "../../data/rag_db"
        )
        self._chroma = None
        self._collection = None
        self._fallback_docs: list[dict] = []
        self._fallback_vectorizer = None
        self._fallback_matrix = None
        self._mode = "none"

        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            from chromadb.config import Settings

            client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = client.get_or_create_collection(
                name="jarvis_knowledge",
                metadata={"hnsw:space": "cosine"},
            )
            self._mode = "chromadb"
            count = self._collection.count()
            logger.info(f"[RAG] ChromaDB ready — {count} chunks indexed")
        except ImportError:
            logger.info("[RAG] ChromaDB not installed — using TF-IDF fallback")
            logger.info("[RAG] Install: pip install chromadb sentence-transformers")
            self._mode = "tfidf"
        except Exception as e:
            logger.warning(f"[RAG] ChromaDB init failed: {e} — TF-IDF fallback")
            self._mode = "tfidf"

    # ── Indexing ──────────────────────────────────────────────────────────────

    def index_directory(
        self,
        directory: str,
        extensions: list[str] = None,
        recursive: bool = True,
    ) -> int:
        """
        Index all files in a directory.
        Returns number of chunks indexed.
        """
        if extensions is None:
            extensions = [".md", ".txt", ".rst"]

        directory = Path(directory).expanduser()
        if not directory.exists():
            logger.warning(f"[RAG] Directory not found: {directory}")
            return 0

        pattern = "**/*" if recursive else "*"
        files = [
            f for f in directory.glob(pattern)
            if f.is_file() and f.suffix.lower() in extensions
        ]

        total_chunks = 0
        for file_path in files:
            try:
                chunks = self._index_file(file_path)
                total_chunks += chunks
            except Exception as e:
                logger.debug(f"[RAG] Skip {file_path.name}: {e}")

        self._rebuild_fallback_index()
        logger.info(f"[RAG] Indexed {len(files)} files → {total_chunks} chunks")
        return total_chunks

    def _index_file(self, file_path: Path) -> int:
        """Index a single file. Returns chunk count."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise RuntimeError(f"Read error: {e}")

        if not text.strip():
            return 0

        # Clean and chunk
        clean = _clean_markdown(text) if file_path.suffix == ".md" else text
        chunks = _chunk_text(clean)

        if not chunks:
            return 0

        source = str(file_path)
        filename = file_path.name

        if self._mode == "chromadb":
            self._upsert_chromadb(chunks, source, filename)
        else:
            for i, chunk in enumerate(chunks):
                self._fallback_docs.append({
                    "id": f"{source}_{i}",
                    "text": chunk,
                    "source": source,
                    "filename": filename,
                })

        return len(chunks)

    def _upsert_chromadb(self, chunks: list[str], source: str, filename: str):
        """Upsert chunks into ChromaDB (idempotent)."""
        ids = [f"{source}_{i}" for i in range(len(chunks))]
        metas = [{"source": source, "filename": filename, "chunk": i}
                 for i in range(len(chunks))]

        # ChromaDB handles embedding internally via default all-MiniLM-L6-v2
        self._collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metas,
        )

    def _rebuild_fallback_index(self):
        """Rebuild TF-IDF index for fallback mode."""
        if self._mode != "tfidf" or not self._fallback_docs:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            import numpy as np

            texts = [d["text"] for d in self._fallback_docs]
            self._fallback_vectorizer = TfidfVectorizer(max_features=10000)
            self._fallback_matrix = self._fallback_vectorizer.fit_transform(texts)
            logger.info(f"[RAG] TF-IDF index built: {len(texts)} chunks")
        except ImportError:
            logger.warning("[RAG] scikit-learn needed for TF-IDF fallback")

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def retrieve(self, query: str, k: int = TOP_K) -> str:
        """
        Retrieve top-k relevant chunks for a query.
        Returns formatted context string for injection into prompt.
        """
        if self._mode == "chromadb":
            return self._retrieve_chromadb(query, k)
        elif self._mode == "tfidf" and self._fallback_matrix is not None:
            return self._retrieve_tfidf(query, k)
        return ""

    def _retrieve_chromadb(self, query: str, k: int) -> str:
        try:
            count = self._collection.count()
            if count == 0:
                return ""

            results = self._collection.query(
                query_texts=[query],
                n_results=min(k, count),
                include=["documents", "metadatas", "distances"],
            )

            chunks = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            for doc, meta, dist in zip(docs, metas, distances):
                # ChromaDB cosine: distance = 1 - similarity
                similarity = 1.0 - dist
                if similarity >= SIMILARITY_THRESHOLD:
                    source = meta.get("filename", "unknown")
                    chunks.append(f"[{source}]\n{doc}")

            if not chunks:
                return ""

            context = "\n\n---\n\n".join(chunks)
            return f"Contexto de tu base de conocimiento personal:\n\n{context}"

        except Exception as e:
            logger.error(f"[RAG] ChromaDB retrieve error: {e}")
            return ""

    def _retrieve_tfidf(self, query: str, k: int) -> str:
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            q_vec = self._fallback_vectorizer.transform([query])
            sims = cosine_similarity(q_vec, self._fallback_matrix)[0]
            top_idx = np.argsort(sims)[::-1][:k]

            chunks = []
            for idx in top_idx:
                if sims[idx] >= SIMILARITY_THRESHOLD:
                    doc = self._fallback_docs[idx]
                    chunks.append(f"[{doc['filename']}]\n{doc['text']}")

            if not chunks:
                return ""

            return "Contexto de tu base de conocimiento:\n\n" + "\n\n---\n\n".join(chunks)

        except Exception as e:
            logger.error(f"[RAG] TF-IDF retrieve error: {e}")
            return ""

    def get_stats(self) -> dict:
        stats = {"mode": self._mode}
        if self._mode == "chromadb" and self._collection:
            stats["chunks"] = self._collection.count()
        elif self._mode == "tfidf":
            stats["chunks"] = len(self._fallback_docs)
        else:
            stats["chunks"] = 0
        return stats

    def clear(self):
        """Clear all indexed data."""
        if self._mode == "chromadb" and self._collection:
            self._collection.delete(where={"chunk": {"$gte": 0}})
        self._fallback_docs = []
        self._fallback_matrix = None
        logger.info("[RAG] Cleared all indexed data")


# ── Obsidian helper ───────────────────────────────────────────────────────────

def index_obsidian_vault(rag: JarvisRAG, vault_path: Optional[str] = None) -> int:
    """
    Index an Obsidian vault.
    Skips: .obsidian/, attachments, templates.
    """
    if vault_path is None:
        # Try common locations
        candidates = [
            os.path.expanduser("~/Documents/OBSIDIAN"),
            os.path.expanduser("~/Obsidian"),
            os.path.expanduser("~/Documents/obsidian"),
            "/mnt/c/Users/Acer Nitro/Documents/OBSIDIAN",
        ]
        vault_path = next((p for p in candidates if os.path.isdir(p)), None)

    if not vault_path:
        logger.warning("[RAG] Obsidian vault not found. Set OBSIDIAN_VAULT_PATH in jarvis.env")
        return 0

    logger.info(f"[RAG] Indexing Obsidian vault: {vault_path}")

    # Skip system folders
    skip_dirs = {".obsidian", ".trash", "attachments", "templates", "Templates"}

    vault = Path(vault_path)
    md_files = [
        f for f in vault.rglob("*.md")
        if not any(part in skip_dirs for part in f.parts)
    ]

    total = 0
    for f in md_files:
        try:
            chunks = rag._index_file(f)
            total += chunks
        except Exception as e:
            logger.debug(f"[RAG] Skip {f.name}: {e}")

    rag._rebuild_fallback_index()
    logger.info(f"[RAG] Obsidian: {len(md_files)} notes → {total} chunks")
    return total


# ── Singleton ─────────────────────────────────────────────────────────────────
_rag_instance: Optional[JarvisRAG] = None


def get_rag() -> JarvisRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = JarvisRAG()
        # Auto-index Obsidian if path set
        vault = os.getenv("OBSIDIAN_VAULT_PATH", "")
        if vault:
            index_obsidian_vault(_rag_instance, vault)
    return _rag_instance
