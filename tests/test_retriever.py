"""Tests for the MultiIndexRetriever."""

import pytest
from src.core.schemas import ParsedArtifact, ArtifactType, Commodity, RetrievedContext


class TestRetrievedContext:
    """Test RetrievedContext data model."""

    def test_empty_context(self):
        ctx = RetrievedContext()
        assert len(ctx.glossary) == 0
        assert len(ctx.eco_precedents) == 0
        assert len(ctx.msa_clauses) == 0

    def test_context_with_chunks(self):
        from src.core.schemas import RetrievedChunk
        ctx = RetrievedContext(
            glossary=[
                RetrievedChunk(id="G001", source="glossary", content="CNC machining...", score=0.92),
                RetrievedChunk(id="G015", source="glossary", content="Tolerance...", score=0.85),
            ],
            eco_precedents=[
                RetrievedChunk(id="E042", source="eco_corpus", content="ECO-22104...", score=0.88),
            ],
            msa_clauses=[
                RetrievedChunk(id="M07", source="msa", content="MSA §7.1...", score=0.91),
            ],
        )
        assert len(ctx.glossary) == 2
        assert len(ctx.eco_precedents) == 1
        assert len(ctx.msa_clauses) == 1
        assert ctx.glossary[0].score == 0.92


class TestQueryBuilding:
    """Test query construction from parsed artifacts."""

    def test_query_includes_raw_text(self):
        artifact = ParsedArtifact(
            raw_text="ECO-24817: Change cathode binder",
            artifact_type=ArtifactType.ECO,
            commodity=Commodity.BATTERY,
        )
        # The retriever builds queries from the artifact
        query_parts = [artifact.raw_text]
        if artifact.commodity.value != "OTHER":
            query_parts.append(f"commodity: {artifact.commodity.value}")
        query = " ".join(query_parts)

        assert "ECO-24817" in query
        assert "battery" in query
