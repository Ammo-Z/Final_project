# ECO-Impact Interpreter

**Leveraging LLM Reasoning to Bridge the Gap Between Technical Engineering Changes and Commercial Supply Chain Decisions**

BU.330.760.T1 Generative AI — Individual Project | Johns Hopkins Carey Business School
Author: Ammo (Leyan) Zhang

---

## 1. Context, User, and Problem

### The User: Global Supply Managers (GSMs)

Global Supply Managers at consumer electronics companies are responsible for managing supplier relationships, negotiating costs, and ensuring on-time delivery of components. They sit at the intersection of engineering and commercial operations during New Product Introduction (NPI) programs.

### The Workflow Being Improved

During an NPI cycle, a GSM receives 10-20 Engineering Change Orders (ECOs) per week from engineering teams. Each ECO is a dense, technical document describing a material substitution, process change, design revision, or component end-of-life notice. A typical ECO looks like this:

> *ECO-24817: Change battery cathode binder from PVDF-A to PVDF-B, effective W38. Supplier claims +$0.42/cell NRE and 5-week requal. Reason: PVDF-A upstream supplier exiting market Q3.*

To act on this, the GSM must:

1. Understand the technical content (what is PVDF? why does a binder change matter?)
2. Assess cost impact (is the $0.42/cell NRE claim justified?)
3. Assess schedule impact (does a 5-week requal hit the critical path?)
4. Check contractual leverage (does the MSA cover supplier-caused EOL?)
5. Formulate a negotiation position and next steps

### Why It Matters

This manual translation process takes **10-15 minutes per ECO** and requires the GSM to cross-reference glossaries, historical ECOs, cost models, and contract clauses across multiple systems. Critical details are frequently missed, leading to:

- Accepting unjustified cost claims (overpaying suppliers by 15-30%)
- Missing schedule risks that delay mass production
- Failing to leverage contractual protections during negotiations

The Technical-Commercial Information Gap is the core problem: engineering teams write for engineers, but GSMs need commercial intelligence to make decisions.

---

## 2. Solution and Design

### What We Built

ECO-Impact Interpreter (Eng2Biz) is a GenAI-powered decision-support tool that automatically transforms raw engineering artifacts into structured **GSM Briefs** — actionable commercial impact reports containing plain-language translation, cost/schedule analysis, risk assessment, and recommended actions with citations.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Engineering Artifact                       │
│         ECO · PCN · Yield Report · DFM Memo · FA Report      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                 ┌─────▼─────┐
                 │  1. PARSE  │  LLM-based entity extraction
                 │            │  (artifact type, commodity, supplier,
                 │            │   part number, tolerances, materials)
                 └─────┬─────┘
                       │
              ┌────────▼────────┐
              │  2. RAG RETRIEVE │  Triple-index knowledge base
              │                  │  Top-3 Glossary + Top-3 ECO
              │                  │  Precedents + Top-2 MSA Clauses
              └────────┬────────┘
                       │
               ┌───────▼───────┐
               │  3. DRAFT     │  Chain-of-Thought reasoning
               │   (CoT)      │  Physical → Process → Cost
               │               │  causal chain analysis
               └───────┬───────┘
                       │
              ┌────────▼────────┐
              │  4. CRITIQUE    │  Self-Reflexion loop
              │  (Self-Refl.)  │  Citation audit, logic check,
              │                 │  completeness validation
              └────────┬────────┘
                       │
               ┌───────▼───────┐
               │  5. FINALIZE  │  Publish or Refuse
               │               │  Confidence scoring
               └───────┬───────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      GSM Brief                               │
│  Translation · Cost Impact · Schedule Impact · Risk          │
│  Recommended Actions · Citations · Confidence Score          │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Choices

**Agentic Pipeline over Monolithic Prompt.** Rather than a single large prompt, the system uses a five-stage pipeline where each stage has a focused role. This enables targeted prompt engineering per stage, independent evaluation of each component, and the self-critique loop that catches errors before output.

**RAG with Triple-Index Knowledge Base.** The retriever queries three separate indices:

- **Glossary (800 entries):** Engineering term definitions with commercial impact annotations. Enables the LLM to understand domain-specific jargon like "PVDF," "requal," or "NRE" in context.
- **ECO Corpus (120 cases):** Historical ECO records with outcomes. Provides precedent-based reasoning (e.g., "a similar binder change in ECO-22104 was resolved at $0 NRE").
- **MSA Clauses (20 sections):** Master Supply Agreement sections covering cost allocation, tooling ownership, quality requirements, etc. Enables contractual grounding for recommendations.

**Chain-of-Thought Drafting.** The drafter follows a three-step causal chain: Physical (what changes mechanically/chemically) then Process (what manufacturing steps are affected) then Cost (what is the financial exposure). This mirrors how an experienced GSM would reason through an ECO.

**Self-Reflexion Critic.** Before publishing, a separate critic agent reviews the draft for: citation faithfulness (every claim must trace to a source), logical consistency, completeness (all five brief sections populated), and confidence calibration. If the critic finds issues, the brief is either revised or withheld.

**Intelligent Refusal.** When the input is too vague or ambiguous (e.g., "Vendor A says it's the film supplier's fault"), the system refuses to generate a brief and instead returns a structured list of missing information and required clarifications. This prevents hallucinated analysis on insufficient data.

### Technology Stack

| Component | Technology |
|-----------|------------|
| LLM | Claude (Anthropic) / GPT-4 (OpenAI) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | ChromaDB |
| Data Models | Pydantic v2 |
| Web UI | Streamlit |
| Language | Python 3.10+ |

---

## 3. Evaluation and Results

### Evaluation Framework

The system is evaluated using a **Model-as-a-Judge** approach with a six-dimension rubric, supplemented by simulated human ratings for inter-rater reliability analysis.

### Test Set

30 synthetic test cases with Gold Standard briefs:

- 25 PUBLISH cases across 5 commodities (battery, display, enclosure, PCB/PCBA, thermal) and 5 artifact types (ECO, PCN, yield excursion, DFM memo, FA report)
- 5 REFUSAL cases designed to test the system's ability to refuse under-specified inputs

### Rubric Dimensions

| Dimension | What It Measures | Scoring |
|-----------|-----------------|---------|
| Translation Accuracy | Does the plain-language summary correctly capture the technical content? | 1-5 scale |
| Completeness | Are all five brief sections (translation, cost, schedule, risk, actions) populated and substantive? | 1-5 scale |
| Citation Faithfulness | What percentage of factual claims are grounded in retrieved sources? | % with valid citation |
| Action Usefulness | Are the recommended actions specific, assigned, and actionable? | 1-5 scale |
| Refusal Correctness | Does the system correctly refuse under-specified inputs and accept well-specified ones? | Accuracy |
| Latency | End-to-end processing time per case | Seconds (p50/p95) |

### Baselines

Two baselines are used for comparison:

1. **Manual Baseline:** A GSM manually cross-referencing ECOs against Excel should-cost models, glossary spreadsheets, and contract PDFs. Average time: 10-15 minutes per ECO. Represents current industry practice.

2. **Prompt-Only Baseline:** A zero-shot LLM call (same model, same input) without RAG retrieval, without Chain-of-Thought structuring, and without self-critique. Isolates the contribution of the agentic pipeline design.

### Expected Results

| Metric | Prompt-Only | Eng2Biz (Full Pipeline) | Target |
|--------|-------------|------------------------|--------|
| Translation Accuracy | ~3.2 | >= 4.2 | >= 4.2 |
| Completeness | ~2.8 | >= 4.0 | >= 4.0 |
| Citation Faithfulness | 0% (no sources) | >= 95% | >= 95% |
| Action Usefulness | ~2.5 | >= 3.8 | >= 3.8 |
| Refusal Correctness | 1/5 | >= 5/6 | >= 5/6 |
| Latency (p50) | ~3s | ~10s | <= 12s |

### Statistical Methods

- **Cohen's Kappa:** Measures inter-rater agreement between the Model-as-a-Judge and simulated human ratings. Target: kappa >= 0.6 (substantial agreement).
- **Paired Bootstrap Test:** Tests statistical significance of score differences between Eng2Biz and the prompt-only baseline (p < 0.05).

---

## 4. Artifact Snapshot

### Decision Cockpit UI

The Streamlit-based Decision Cockpit provides a split-pane interface:

- **Left pane:** Source artifact text with highlighted technical terms (hover for definitions)
- **Right pane:** Structured GSM Brief with cost trend, schedule impact, risk level, and recommended actions
- **Bottom bar:** Quality scores across five dimensions (Translation, Completeness, Citations, Actions, Overall)

![Decision Cockpit — Published Brief](docs/images/cockpit_published.png)

*Above: A battery binder ECO (CASE-01) analyzed in Demo Mode. The system identifies the PVDF material change, retrieves relevant glossary terms and MSA clauses, and recommends rejecting the supplier's NRE claim based on contractual precedent.*

### Refusal Example

![Decision Cockpit — Refusal](docs/images/cockpit_refusal.png)

*Above: A vague Slack message (FAIL-01) triggers the refusal pathway. The system identifies four missing pieces of information and returns structured clarification requests instead of generating a potentially unreliable brief.*

### Sample Input / Output

**Input (ECO):**
```
ECO-24817: Change battery cathode binder from PVDF-A to PVDF-B,
effective W38. Supplier claims +$0.42/cell NRE and 5-week requal.
Reason: PVDF-A upstream supplier exiting market Q3.
```

**Output (GSM Brief — key fields):**

| Field | Value |
|-------|-------|
| Translation | Supplier is changing a key cathode binder material (PVDF-A to PVDF-B) because PVDF-A's supplier is exiting the market. They are requesting a $0.42/cell premium and 5 weeks for re-qualification. |
| Cost Trend | UP — $5.0M claimed, $0 expected after negotiation |
| Schedule | +5 weeks requal (W38 to W43). If MP >= W44, schedule intact. |
| Risk | MEDIUM — low material risk if data matches; single-source risk on PVDF-B |
| Action 1 | Reject NRE claim citing MSA 7.1 — supplier-caused EOL = supplier cost [M07, E015] |
| Action 2 | Kick off requal at W38; request PVDF-B data package by W36 [G051] |
| Action 3 | Validate MP date buffer vs W43 completion with OPM |
| Confidence | 89% |

---

## Setup and Usage Instructions

### Prerequisites

- Python 3.10 or higher
- pip package manager
- (Optional) An Anthropic or OpenAI API key for Live mode

### Step 1: Clone the Repository

```bash
git clone https://github.com/Ammo-Z/Final_project.git
cd Final_project
```

### Step 2: Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application (Demo Mode)

No API key is needed for Demo Mode. The app ships with pre-computed sample results.

```bash
streamlit run src/ui/app.py
```

Open http://localhost:8501 in your browser.

### Step 5: Try It Out

1. In the left sidebar, select a sample ECO from the dropdown (e.g., "CASE-01: Battery Binder")
2. Click **Load Sample** to populate the input area
3. Click **Analyze** to run the demo analysis
4. Explore the GSM Brief output on the right, quality scores at the bottom, and expandable citations on the left
5. Try "FAIL-01: Vague (Refuse)" to see the refusal pathway in action

### Step 6 (Optional): Live Mode with API Key

To run with actual LLM calls instead of demo data:

```bash
cp .env.example .env
# Edit .env and add your API key:
#   ANTHROPIC_API_KEY=sk-ant-...
#   or
#   OPENAI_API_KEY=sk-...
```

Build the RAG index:
```bash
python scripts/build_index.py
```

Then switch to "Live Analysis (API)" in the sidebar.

### Running the Evaluation Suite

```bash
python -m src.evaluation.run_eval --test-set data/test_cases/test_cases_30.json
```

This runs all 30 test cases through the Model-as-a-Judge scorer and outputs dimension-level scores, Cohen's kappa, and bootstrap significance tests.

---

## Project Structure

```
eco-impact-interpreter/
├── README.md                         # This file
├── requirements.txt                  # Python dependencies
├── .env.example                      # API key template
├── configs/
│   └── settings.yaml                 # Central configuration
├── data/
│   ├── glossary/
│   │   └── glossary_800.json         # 800-entry engineering glossary
│   ├── eco_corpus/
│   │   └── eco_corpus_120.json       # 120-case synthetic ECO history
│   ├── msa_templates/
│   │   └── msa_template.json         # 20-section MSA template
│   └── test_cases/
│       └── test_cases_30.json        # 30 test cases + Gold Standard briefs
├── prompts/
│   ├── parser_v1.md                  # Entity extraction prompt
│   ├── drafting_v1.md                # Chain-of-Thought drafting prompt
│   ├── critic_v1.md                  # Self-critique prompt
│   └── judge_v1.md                   # Model-as-a-Judge scoring prompt
├── src/
│   ├── core/
│   │   ├── pipeline.py               # End-to-end pipeline orchestrator
│   │   ├── parser.py                 # LLM-based structural parser
│   │   └── schemas.py                # Pydantic data models
│   ├── rag/
│   │   ├── indexer.py                # ChromaDB index builder
│   │   └── retriever.py              # Multi-index RAG retriever
│   ├── agents/
│   │   ├── drafter.py                # CoT drafting agent
│   │   └── critic.py                 # Self-reflexion critic agent
│   ├── ui/
│   │   ├── app.py                    # Streamlit main application
│   │   └── components.py             # Reusable UI components
│   ├── evaluation/
│   │   ├── run_eval.py               # Evaluation orchestrator
│   │   ├── judge.py                  # Model-as-a-Judge scorer
│   │   └── metrics.py                # Cohen's kappa, bootstrap tests
│   └── utils/
│       ├── llm_client.py             # Unified LLM API wrapper
│       └── logger.py                 # Structured pipeline logging
├── scripts/
│   └── build_index.py                # RAG index builder script
├── tests/
│   ├── test_parser.py                # Parser unit tests
│   ├── test_retriever.py             # Retriever unit tests
│   └── test_pipeline.py              # Integration tests
└── docs/
    └── images/                       # Screenshots for README
```

## Synthetic Data Disclaimer

All data used in this project is **100% synthetic**. No proprietary engineering documents, supplier agreements, or real company data is included. The glossary, ECO corpus, MSA clauses, and test cases were generated to be realistic but entirely fictional.

## Governance

- This tool is designed as **decision support**, not decision automation
- Must NOT be trusted for: final cost decisions exceeding $250K, supplier-facing communications, or contract re-interpretation
- Production deployment would require internal LLM infrastructure and human-in-the-loop validation

## License

This project is for academic purposes (JHU Carey Business School BU.330.760.T1).
