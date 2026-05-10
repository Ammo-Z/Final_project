"""Multi-Index RAG Retriever — Query glossary, ECO corpus, and MSA indices."""

from __future__ import annotations
import json
from typing import Optional

import chromadb
from chromadb.config import Settings

from ..core.schemas import ParsedArtifact, RetrievedChunk, RetrievedContext
from ..utils.logger import PipelineLogger


class MultiIndexRetriever:
    """Retrieve context from triple-index RAG knowledge base.

    Performs per-index retrieval with configurable top-K:
    - Glossary: Top-3 (technical term definitions + commercial impact)
    - ECO Corpus: Top-3 (historical precedents for similar changes)
    - MSA Clauses: Top-2 (relevant contract provisions)
    """

    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        embedding_model: str = "all-MiniLM-L6-v2",
        glossary_top_k: int = 3,
        eco_corpus_top_k: int = 3,
        msa_top_k: int = 2,
        logger: Optional[PipelineLogger] = None,
    ):
        self.glossary_top_k = glossary_top_k
        self.eco_corpus_top_k = eco_corpus_top_k
        self.msa_top_k = msa_top_k
        self.logger = logger or PipelineLogger()

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
            self.embed_fn = None

        # Get collections
        try:
            self.glossary_col = self.client.get_collection("glossary_index", embedding_function=self.embed_fn)
            self.eco_col = self.client.get_collection("eco_corpus_index", embedding_function=self.embed_fn)
            self.msa_col = self.client.get_collection("msa_index", embedding_function=self.embed_fn)
        except Exception as e:
            self.logger.warning(f"Could not load one or more collections: {e}")
            self.glossary_col = None
            self.eco_col = None
            self.msa_col = None

    def retrieve(self, parsed_artifact: ParsedArtifact) -> RetrievedContext:
        """Retrieve relevant context from all three indices.

        Args:
            parsed_artifact: Output from the Parser stage

        Returns:
            RetrievedContext with glossary, ECO precedent, and MSA results
        """
        self.logger.start_timer("retriever")
        self.logger.info("Retrieving context from triple-index RAG")

        # Build query from parsed artifact
        query = self._build_query(parsed_artifact)

        # Retrieve from each index
        glossary_results = self._query_collection(
            self.glossary_col, query, self.glossary_top_k, "glossary"
        )
        eco_results = self._query_collection(
            self.eco_col, query, self.eco_corpus_top_k, "eco_corpus"
        )
        msa_results = self._query_collection(
            self.msa_col, query, self.msa_top_k, "msa"
        )

        context = RetrievedContext(
            glossary=glossary_results,
            eco_precedents=eco_results,
            msa_clauses=msa_results,
        )

        elapsed = self.logger.stop_timer("retriever")
        self.logger.info(
            f"Retrieved: {len(glossary_results)} glossary, "
            f"{len(eco_results)} ECO precedents, "
            f"{len(msa_results)} MSA clauses ({elapsed:.1f}s)"
        )

        return context

    def _build_query(self, artifact: ParsedArtifact) -> str:
        """Build a search query string from parsed artifact."""
        parts = [artifact.raw_text]

        # Add entity details for better matching
        for mat in artifact.entities.materials:
            parts.append(f"material: {mat.name}")
        for proc in artifact.entities.processes:
            parts.append(f"process: {proc.name}")
        for tol in artifact.entities.tolerances:
            parts.append(f"tolerance: {tol.dimension}")
        for risk in artifact.entities.risk_indicators:
            parts.append(f"risk: {risk.detail or risk.type}")

        # Add commodity for better relevance
        if artifact.commodity.value != "OTHER":
            parts.append(f"commodity: {artifact.commodity.value}")

        return " ".join(parts)

    def _query_collection(
        self,
        collection,
        query: str,
        top_k: int,
        source: str,
    ) -> list[RetrievedChunk]:
        """Query a single ChromaDB collection."""
        if collection is None:
            self.logger.warning(f"Collection '{source}' not available")
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            chunks = []
            for i in range(len(results["ids"][0])):
                chunk = RetrievedChunk(
                    id=results["ids"][0][i],
                    source=source,
                    content=results["documents"][0][i],
                    score=1.0 - results["distances"][0][i],  # Convert distance to similarity
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            self.logger.error(f"Error querying {source}: {e}")
            return []

    def format_context_for_prompt(self, context: RetrievedContext) -> dict[str, str]:
        """Format retrieved context as strings for prompt injection.

        Returns:
            Dict with keys: glossary_context, eco_corpus_context, msa_context
        """
        def format_chunks(chunks: list[RetrievedChunk], prefix: str) -> str:
            if not chunks:
                return "No relevant matches found."
            lines = []
            for chunk in chunks:
                lines.append(f"[{chunk.id}] (score: {chunk.score:.2f}) {chunk.content}")
            return "\n\n".join(lines)

        return {
            "glossary_context": format_chunks(context.glossary, "G"),
            "eco_corpus_context": format_chunks(context.eco_precedents, "E"),
            "msa_context": format_chunks(context.msa_clauses, "M"),
        }
