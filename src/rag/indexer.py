"""RAG Index Builder — Build and manage ChromaDB vector indices."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings


class RAGIndexer:
    """Build and manage triple-index RAG knowledge base using ChromaDB."""

    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model

        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_dir,
            anonymized_telemetry=False,
        ))

        # Initialize embedding function
        try:
            from chromadb.utils import embedding_functions
            self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embedding_model
            )
        except Exception:
            self.embed_fn = None  # Fall back to ChromaDB default

    def build_glossary_index(self, data_path: str, collection_name: str = "glossary_index"):
        """Build vector index from glossary JSON."""
        data = self._load_json(data_path)
        print(f"Building glossary index: {len(data)} entries")

        collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embed_fn,
            metadata={"source": "glossary", "hnsw:space": "cosine"},
        )

        # Prepare documents
        ids = []
        documents = []
        metadatas = []

        for entry in data:
            doc_text = (
                f"{entry['term']} ({entry['full_name']}): {entry['definition']}. "
                f"Commercial Impact: {entry['commercial_impact']}"
            )
            ids.append(entry["id"])
            documents.append(doc_text)
            metadatas.append({
                "term": entry["term"],
                "category": entry["category"],
                "cost_direction": entry.get("cost_direction", "NEUTRAL"),
                "source": "glossary",
            })

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            collection.upsert(
                ids=ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        print(f"Glossary index built: {collection.count()} documents")
        return collection

    def build_eco_corpus_index(self, data_path: str, collection_name: str = "eco_corpus_index"):
        """Build vector index from ECO corpus JSON."""
        data = self._load_json(data_path)
        print(f"Building ECO corpus index: {len(data)} entries")

        collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embed_fn,
            metadata={"source": "eco_corpus", "hnsw:space": "cosine"},
        )

        ids = []
        documents = []
        metadatas = []

        for entry in data:
            doc_text = (
                f"ECO {entry['eco_number']} ({entry['commodity']}): "
                f"{entry['change_description']} "
                f"Impact: {entry['impact_summary']} "
                f"Resolution: {entry['resolution']}"
            )
            ids.append(entry["id"])
            documents.append(doc_text)
            metadatas.append({
                "eco_number": entry["eco_number"],
                "commodity": entry["commodity"],
                "cost_trend": entry["cost_trend"],
                "date": entry["date"],
                "supplier": entry["supplier"],
                "source": "eco_corpus",
            })

        batch_size = 100
        for i in range(0, len(ids), batch_size):
            collection.upsert(
                ids=ids[i : i + batch_size],
                documents=documents[i : i + batch_size],
                metadatas=metadatas[i : i + batch_size],
            )

        print(f"ECO corpus index built: {collection.count()} documents")
        return collection

    def build_msa_index(self, data_path: str, collection_name: str = "msa_index"):
        """Build vector index from MSA template JSON."""
        data = self._load_json(data_path)
        print(f"Building MSA index: {len(data)} entries")

        collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embed_fn,
            metadata={"source": "msa", "hnsw:space": "cosine"},
        )

        ids = []
        documents = []
        metadatas = []

        for entry in data:
            doc_text = (
                f"MSA {entry['section_number']} {entry['title']}: "
                f"{entry['full_text']} "
                f"Key provisions: {'; '.join(entry['key_provisions'])}. "
                f"ECO relevance: {entry['relevance_to_eco']}"
            )
            ids.append(entry["id"])
            documents.append(doc_text)
            metadatas.append({
                "section": entry["section_number"],
                "title": entry["title"],
                "negotiation_lever": entry["negotiation_lever"],
                "source": "msa",
            })

        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        print(f"MSA index built: {collection.count()} documents")
        return collection

    def build_all(
        self,
        glossary_path: str = "./data/glossary/glossary_800.json",
        eco_corpus_path: str = "./data/eco_corpus/eco_corpus_120.json",
        msa_path: str = "./data/msa_templates/msa_template.json",
    ):
        """Build all three indices."""
        print("=" * 60)
        print("Building Triple-Index RAG Knowledge Base")
        print("=" * 60)

        self.build_glossary_index(glossary_path)
        self.build_eco_corpus_index(eco_corpus_path)
        self.build_msa_index(msa_path)

        if hasattr(self.client, "persist"):
            self.client.persist()

        print("\nAll indices built and persisted.")
        print(f"Persist directory: {self.persist_dir}")

    @staticmethod
    def _load_json(path: str) -> list[dict]:
        """Load JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
