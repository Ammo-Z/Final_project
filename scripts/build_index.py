#!/usr/bin/env python3
"""Build RAG vector indices from synthetic knowledge base data."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.indexer import RAGIndexer


def main():
    print("ECO-Impact Interpreter — RAG Index Builder")
    print("=" * 50)

    indexer = RAGIndexer(
        persist_dir="./chroma_db",
        embedding_model="all-MiniLM-L6-v2",
    )

    indexer.build_all(
        glossary_path="./data/glossary/glossary_800.json",
        eco_corpus_path="./data/eco_corpus/eco_corpus_120.json",
        msa_path="./data/msa_templates/msa_template.json",
    )

    print("\nDone! You can now run the pipeline or Streamlit app.")


if __name__ == "__main__":
    main()
