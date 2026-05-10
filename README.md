# ECO-Impact Interpreter

**Technical-to-Commercial Bridge for Global Supply Managers**

> *Leveraging LLM Reasoning to Bridge the Gap Between Technical Engineering Changes and Commercial Supply Chain Decisions*

**BU.330.760.T1 Generative AI — Individual Project**
**Johns Hopkins Carey Business School**
**Author: Ammo (Leyan) Zhang**

---

## Overview

ECO-Impact Interpreter (Eng2Biz) is a generative AI decision-support tool that transforms unstructured, technical Engineering Change Order (ECO) descriptions into actionable **GSM Briefs** — structured commercial impact reports for Global Supply Managers.

The system uses an **agentic pipeline** with Chain-of-Thought reasoning, RAG-augmented contextualization, and self-critique loops to bridge the "Technical-Commercial Information Gap" in New Product Introduction (NPI) workflows.

### Architecture

```
Engineering Artifact  →  Eng2Biz (GenAI)  →  GSM Brief
ECO · PCN · Yield report   Parse → RAG Retrieve     Translation · Cost · Schedule
DFM memo · FA report       Reason → Draft → Critique  Risk · Actions + Citations
```

### Pipeline Stages

1. **Input & Parser** — Extracts technical entities (tolerances, materials, process types)
2. **RAG Retriever** — Queries triple-index knowledge base (Glossary, ECO History, MSA Clauses)
3. **Drafting Agent (CoT)** — Chain-of-Thought reasoning through physical-to-commercial causal chain
4. **Critic Agent (Self-Reflexion)** — Validates logical consistency and citation faithfulness
5. **Output Synthesis** — Generates structured GSM Brief with confidence scores

## Quick Start

### Prerequisites

- Python 3.10+
- An Anthropic API key (or OpenAI API key)

### Installation

```bash
git clone https://github.com/ammo-z/eco-impact-interpreter.git
cd eco-impact-interpreter

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
# Edit .env and add your API key
```

### Build RAG Index

```bash
python scripts/build_index.py
```

### Run the Application

```bash
# Streamlit UI
streamlit run src/ui/app.py

# CLI mode
python -m src.core.pipeline --input "ECO-24817: Change battery cathode binder from PVDF-A to PVDF-B..."
```

### Run Evaluation

```bash
python -m src.evaluation.run_eval --test-set data/test_cases/test_cases_30.json
```

## Project Structure

```
eco-impact-interpreter/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── configs/
│   └── settings.yaml              # Central configuration
├── data/
│   ├── glossary/
│   │   └── glossary_800.json      # 800-entry engineering glossary
│   ├── eco_corpus/
│   │   └── eco_corpus_120.json    # 120-case synthetic ECO history
│   ├── msa_templates/
│   │   └── msa_template.json      # 20-section MSA template
│   └── test_cases/
│       └── test_cases_30.json     # 30-case evaluation set + Gold Briefs
├── prompts/
│   ├── drafting_v1.md             # Chain-of-Thought drafting prompt
│   ├── critic_v1.md               # Self-critique prompt
│   ├── judge_v1.md                # Model-as-a-Judge scoring prompt
│   └── parser_v1.md               # Entity extraction prompt
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── pipeline.py            # End-to-end orchestration
│   │   ├── parser.py              # Structural parser
│   │   └── schemas.py             # Pydantic data models
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── indexer.py             # Build & manage vector indices
│   │   └── retriever.py           # Multi-index retrieval
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── drafter.py             # CoT drafting agent
│   │   └── critic.py              # Self-reflexion critic agent
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py                 # Streamlit main app
│   │   └── components.py          # UI components
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── run_eval.py            # Evaluation orchestrator
│   │   ├── judge.py               # Model-as-a-Judge
│   │   └── metrics.py             # Cohen's κ, rubric scoring
│   └── utils/
│       ├── __init__.py
│       ├── llm_client.py          # LLM API wrapper
│       └── logger.py              # Structured logging
├── scripts/
│   └── build_index.py             # RAG index builder script
├── tests/
│   ├── test_parser.py
│   ├── test_retriever.py
│   └── test_pipeline.py
└── docs/
    └── images/
```

## Knowledge Base (Synthetic Data)

All data is **100% synthetic** — no real proprietary data is used.

| Index | Entries | Description |
|-------|---------|-------------|
| Glossary | 800 | Engineering-to-commercial term mappings |
| ECO Corpus | 120 | Historical ECO cases with outcomes |
| MSA Template | 20 sections | Master Supply Agreement clauses |

## Evaluation

### Rubric Dimensions (scored 1–5)

| Dimension | Metric | Target |
|-----------|--------|--------|
| Translation Accuracy | Rubric 1–5 (judge + human) | Mean >= 4.2 |
| Completeness | Rubric 1–5 | Mean >= 4.0 |
| Citation Faithfulness | % claims with valid citations | >= 95% |
| Action Usefulness | Rubric 1–5 | Mean >= 3.8 |
| Refusal Correctness | Accuracy on under-spec cases | >= 5/6 |
| Latency | p50 / p95 end-to-end | <= 12s / <= 25s |

### Baselines

- **Manual Baseline**: GSM manually cross-referencing with Excel Should-Cost models (10 min/case)
- **Prompt-Only Baseline**: Zero-shot LLM without RAG or agentic loops

## Governance

- **Must NOT be trusted for**: final cost decisions >$250k, supplier-facing communication, contract re-interpretation
- **Data privacy**: 100% synthetic data; production deployment would run inside internal LLM infrastructure

## License

This project is for academic purposes (JHU Carey Business School BU.330.760.T1).
