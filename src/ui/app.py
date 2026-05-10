"""ECO-Impact Interpreter — Streamlit Decision Cockpit.

The main web application providing a zero-friction analysis interface
for Global Supply Managers to interpret Engineering Change Orders.
"""

import json
import sys
import time
from pathlib import Path

import streamlit as st

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.ui.components import (
    render_confidence_badge,
    render_engineering_context,
    render_gsm_brief,
    render_refusal,
    render_score_dashboard,
    render_cost_trend_badge,
    render_risk_badge,
)

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ECO-Impact Interpreter",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8e 100%);
        color: white;
        padding: 20px 30px;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8em; }
    .main-header p { color: #cbd5e1; margin: 4px 0 0 0; font-size: 0.95em; }
    .metric-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .stExpander { border: 1px solid #e2e8f0 !important; border-radius: 8px !important; }
    div[data-testid="stVerticalBlock"] > div:has(> div.stMarkdown) { gap: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("""
<div class="main-header">
    <h1>🔧 ECO-Impact Interpreter</h1>
    <p>Technical-to-Commercial Bridge for Global Supply Managers | Eng2Biz Decision Cockpit</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    mode = st.radio(
        "Mode",
        ["Live Analysis (API)", "Demo Mode (Sample Data)"],
        index=1,
        help="Demo mode uses pre-computed results without API calls",
    )

    st.divider()
    st.markdown("### 📊 Pipeline Settings")

    enable_critique = st.checkbox("Enable Self-Critique", value=True)
    enable_citations = st.checkbox("Show Citations", value=True)

    st.divider()
    st.markdown("### 📋 Sample ECOs")

    sample_ecos = {
        "CASE-01: Battery Binder ECO": (
            "ECO-24817: Change battery cathode binder from PVDF-A to PVDF-B, "
            "effective W38. Supplier claims +$0.42/cell NRE and 5-week requal. "
            "Reason: PVDF-A upstream supplier exiting market Q3."
        ),
        "CASE-02: Display Driver IC EOL": (
            "PCN-2025-0342: Display driver IC (P/N: DD-IC-7820A) end-of-life notice. "
            "Last time buy deadline: 2025-08-15. Recommended replacement: DD-IC-7821B. "
            "Pin-compatible but requires firmware update. Supplier: BOE Technology."
        ),
        "CASE-03: Enclosure Anodize Yield": (
            "YIELD EXCURSION REPORT: Batch #W37-ENC-042. Anodize color match "
            "failure rate spiked to 12% (normal: 2-3%). Root cause: Type II anodize "
            "bath chemistry drift. Affects P/N: ENC-88421-A. Supplier: Lens Technology."
        ),
        "CASE-04: Solder Joint Fatigue FA": (
            "FA-2025-0089: Field return analysis — solder joint fatigue on U12 (BGA-256, "
            "0.5mm pitch). 23 units returned from 50K shipment. Failure mode: crack "
            "propagation at corner balls after 800 thermal cycles. Supplier: Jabil."
        ),
        "CASE-05: EVT Exit Readout": (
            "EVT EXIT READOUT: Product Alpha, Build W35. Marginal CTQs identified: "
            "(1) Battery impedance 15% above target at -10°C, (2) Display brightness "
            "non-uniformity at 8% (spec: ≤5%), (3) Enclosure gap at antenna band "
            "0.12mm (spec: ≤0.10mm). DVT entry decision pending."
        ),
        "FAIL-01: Vague Slack (Should Refuse)": (
            "We got an update from Vendor A on the battery issue. They're saying "
            "the yield problem is the film supplier's fault, not theirs. "
            "Recommend holding the PO."
        ),
    }

    selected_sample = st.selectbox("Load sample:", list(sample_ecos.keys()))
    if st.button("Load Sample", use_container_width=True):
        st.session_state["input_text"] = sample_ecos[selected_sample]

    st.divider()
    st.markdown(
        '<div style="font-size:0.75em;color:#94a3b8;">'
        'v1.0.0 | JHU Carey BU.330.760.T1<br>'
        'All data is 100% synthetic'
        '</div>',
        unsafe_allow_html=True,
    )

# ─── Main Content ────────────────────────────────────────────────────────────

# Input area
st.markdown("### 📥 Input Engineering Artifact")
input_text = st.text_area(
    "Paste ECO, PCN, yield report, DFM memo, or FA report:",
    value=st.session_state.get("input_text", ""),
    height=120,
    placeholder="e.g., ECO-24817: Change battery cathode binder from PVDF-A to PVDF-B...",
)

col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
with col_btn1:
    analyze_btn = st.button("🔍 Analyze", type="primary", use_container_width=True)
with col_btn2:
    clear_btn = st.button("🗑️ Clear", use_container_width=True)

if clear_btn:
    st.session_state["input_text"] = ""
    st.session_state.pop("result", None)
    st.rerun()

# ─── Analysis ────────────────────────────────────────────────────────────────

if analyze_btn and input_text.strip():
    if mode == "Live Analysis (API)":
        # Live mode — use actual pipeline
        with st.spinner("🔄 Running Eng2Biz pipeline... (Parse → Retrieve → Draft → Critique)"):
            try:
                from src.core.pipeline import Eng2BizPipeline
                pipeline = Eng2BizPipeline()
                result = pipeline.run(input_text)
                st.session_state["result"] = result.model_dump()
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.info("💡 Make sure your API key is configured in .env and RAG indices are built.")
                st.stop()
    else:
        # Demo mode — simulate with pre-built sample results
        with st.spinner("🔄 Simulating analysis..."):
            time.sleep(1.5)  # Simulate processing
            st.session_state["result"] = _generate_demo_result(input_text)

# ─── Display Results ─────────────────────────────────────────────────────────

if "result" in st.session_state:
    result = st.session_state["result"]

    # Check for refusal
    if result.get("refusal"):
        st.markdown("---")
        render_refusal(result["refusal"])
    elif result.get("brief"):
        brief = result["brief"]
        parsed = result.get("parsed_artifact", {})
        context = result.get("retrieved_context", {})
        review = result.get("critic_review")

        # Header bar with metadata
        st.markdown("---")
        header_cols = st.columns([1, 1, 1, 1, 1])
        with header_cols[0]:
            atype = parsed.get("artifact_type", "ECO")
            st.markdown(f'<span style="background:#3b82f6;color:white;padding:4px 12px;border-radius:6px;font-weight:600;">{atype}</span>', unsafe_allow_html=True)
        with header_cols[1]:
            st.markdown(f"**{parsed.get('artifact_id', 'N/A')}**")
        with header_cols[2]:
            commodity = parsed.get("commodity", "N/A")
            st.markdown(f"🏭 {commodity}")
        with header_cols[3]:
            st.markdown(render_confidence_badge(brief.get("overall_confidence", 0)), unsafe_allow_html=True)
        with header_cols[4]:
            status = "✅ Published" if result.get("is_published") else "⏳ Pending Review"
            st.markdown(status)

        st.markdown("")

        # Two-column strategic card
        left_col, right_col = st.columns([1, 1])

        with left_col:
            glossary_matches = context.get("glossary", [])
            render_engineering_context(
                result.get("input_text", input_text),
                glossary_matches,
            )

            # Show ECO precedents and MSA clauses
            if enable_citations:
                eco_precedents = context.get("eco_precedents", [])
                msa_clauses = context.get("msa_clauses", [])

                if eco_precedents:
                    st.markdown("**ECO Precedents:**")
                    for chunk in eco_precedents:
                        cid = chunk.get("id", "") if isinstance(chunk, dict) else ""
                        content = chunk.get("content", "") if isinstance(chunk, dict) else ""
                        with st.expander(f"📎 {cid}"):
                            st.markdown(content)

                if msa_clauses:
                    st.markdown("**MSA Clauses:**")
                    for chunk in msa_clauses:
                        cid = chunk.get("id", "") if isinstance(chunk, dict) else ""
                        content = chunk.get("content", "") if isinstance(chunk, dict) else ""
                        with st.expander(f"📎 {cid}"):
                            st.markdown(content)

        with right_col:
            render_gsm_brief(brief)

        # Score dashboard
        st.markdown("---")
        render_score_dashboard(brief, review)

        # Pipeline metrics
        with st.expander("📈 Pipeline Metrics"):
            m_cols = st.columns(4)
            with m_cols[0]:
                st.metric("Latency", f"{result.get('latency_seconds', 0):.1f}s")
            with m_cols[1]:
                st.metric("Tokens", f"{result.get('total_tokens', 0):,}")
            with m_cols[2]:
                st.metric("Cost", f"${result.get('estimated_cost_usd', 0):.4f}")
            with m_cols[3]:
                critic_status = "PASS" if review and review.get("review_passed") else "N/A"
                st.metric("Critic", critic_status)

        # Raw JSON output
        with st.expander("🔧 Raw JSON Output"):
            st.json(brief)

elif analyze_btn:
    st.warning("Please enter an engineering artifact to analyze.")


# ─── Demo Result Generator ──────────────────────────────────────────────────

def _generate_demo_result(input_text: str) -> dict:
    """Generate a simulated pipeline result for demo mode."""
    # Detect if this should be a refusal
    refusal_keywords = ["vendor a", "vague", "the issue", "they're saying"]
    is_refusal = sum(1 for kw in refusal_keywords if kw in input_text.lower()) >= 2

    if is_refusal:
        return {
            "case_id": "DEMO",
            "input_text": input_text,
            "parsed_artifact": {
                "artifact_type": "OTHER",
                "commodity": "OTHER",
                "parse_confidence": 0.25,
                "ambiguities": ["Vague supplier reference", "No artifact ID", "No part number"],
                "raw_text": input_text,
            },
            "retrieved_context": {"glossary": [], "eco_precedents": [], "msa_clauses": []},
            "refusal": {
                "is_refusal": True,
                "reason": "Insufficient information to generate a reliable GSM Brief. Parse confidence: 0.25",
                "missing_info": [
                    "Supplier ID or MSA number — 'Vendor A' is not a unique identifier",
                    "Part number or commodity specification",
                    "Artifact reference (ECO#, PCN#, FA#)",
                    "Supporting data for the yield claim",
                ],
                "required_clarifications": [
                    "Please provide the supplier's MSA number or full legal name",
                    "Please provide the specific part number and commodity",
                    "Please provide the ECO or FA number for this issue",
                    "Please provide test data or FA report supporting the blame claim",
                ],
            },
            "brief": None,
            "is_published": False,
            "latency_seconds": 1.5,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        }

    # Generate a sample published brief
    return {
        "case_id": "DEMO",
        "input_text": input_text,
        "parsed_artifact": {
            "artifact_id": "ECO-DEMO",
            "artifact_type": "ECO",
            "commodity": "battery",
            "supplier_id": "SUP-001",
            "part_number": "BAT-001-A",
            "parse_confidence": 0.88,
            "ambiguities": [],
            "raw_text": input_text,
            "entities": {"materials": [], "tolerances": [], "processes": []},
        },
        "retrieved_context": {
            "glossary": [
                {"id": "G051", "source": "glossary", "content": "PVDF (Polyvinylidene Fluoride): Binder material for electrode coatings. Commercial Impact: PVDF grade changes may require slurry reformulation and coating line validation — 3-6 week requal.", "score": 0.92, "metadata": {"term": "PVDF", "category": "Battery/Cell"}},
                {"id": "G059", "source": "glossary", "content": "NRE (Non-Recurring Engineering): One-time engineering/tooling cost. Commercial Impact: NRE is amortized over production volume.", "score": 0.87, "metadata": {"term": "NRE", "category": "Battery/Cell"}},
                {"id": "G060", "source": "glossary", "content": "Requal (Requalification): Re-testing and re-approval of changed component. Commercial Impact: Requal typically 4-8 weeks for mechanical, 8-16 weeks for battery/safety-critical.", "score": 0.85, "metadata": {"term": "Requal", "category": "Battery/Cell"}},
            ],
            "eco_precedents": [
                {"id": "E015", "source": "eco_corpus", "content": "ECO-22104 (battery): Changed cathode active material supplier. Impact: +$0.18/cell, 6-week requal. Resolution: Accepted after negotiating NRE split 50/50.", "score": 0.89, "metadata": {"commodity": "battery", "cost_trend": "UP"}},
            ],
            "msa_clauses": [
                {"id": "M07", "source": "msa", "content": "MSA §7.1 Tooling & NRE: Supplier-caused EOL changes are supplier-funded. Buyer-initiated changes split NRE per volume tier.", "score": 0.91, "metadata": {"section": "§7.0", "title": "Tooling Ownership"}},
            ],
        },
        "brief": {
            "translation": {
                "en": "Supplier is changing a key cathode binder material (PVDF-A → PVDF-B) because PVDF-A's own supplier is exiting the market. They are requesting a $0.42/cell premium and 5 weeks for re-qualification.",
                "zh": "因为PVDF-A上游停产，将正极粘结剂从PVDF-A更换为PVDF-B，要求Apple支付每颗电芯$0.42 NRE并等待5周重新认证。",
            },
            "cost_impact": {
                "trend": "UP",
                "unit_price_delta": "+$0.42/cell (claimed NRE)",
                "nre_estimate": "$0.42/cell × 12M units = ~$5.0M claimed",
                "reasoning": "Per MSA §7.1 [M07], supplier-caused EOL changes are supplier-funded — claim is likely rejectable. Precedent ECO-22104 [E015]: identical scenario, $0 NRE accepted.",
                "total_exposure": "$5.0M claimed, $0 expected after negotiation",
            },
            "schedule_impact": {
                "lead_time_delta_weeks": 5,
                "requal_needed": True,
                "critical_path_risk": "5-week requal from W38 → complete W43. If MP ≥ W44, schedule intact.",
                "milestone_impact": "Confirm MP gate with OPM.",
            },
            "risk_assessment": {
                "level": "MEDIUM",
                "factors": [
                    "Material change is low-risk if PVDF-B electrochemical data matches PVDF-A",
                    "Single-source risk on new PVDF-B supplier",
                ],
                "mitigations": [
                    "Request qualification data from supplier",
                    "Evaluate second PVDF-B source",
                ],
            },
            "recommended_actions": [
                {"action": "Reject NRE claim in writing citing MSA §7.1; supplier-caused EOL = supplier cost", "owner": "Sr. GSM", "confidence": 0.92, "requires_approval_from": None, "citation_refs": ["M07", "E015"]},
                {"action": "Kick off 5-week requal clock at W38; request PVDF-B data package by W36", "owner": "GSM (you)", "confidence": 0.88, "requires_approval_from": None, "citation_refs": ["G051"]},
                {"action": "Validate MP date buffer vs W43 re-qual completion with OPM", "owner": "OPM", "confidence": 0.85, "requires_approval_from": None, "citation_refs": []},
            ],
            "citations_used": {"glossary": ["G051", "G059", "G060"], "eco_precedents": ["E015"], "msa_clauses": ["M07"]},
            "overall_confidence": 0.89,
            "chain_of_thought": "Step 1 (Physical): PVDF binder change affects electrode coating adhesion and slurry viscosity. PVDF-B must match PVDF-A's binding strength and electrochemical stability. Step 2 (Process): Requires slurry reformulation, coating line parameter adjustment, and formation cycling validation. 5-week requal is reasonable for battery chemistry changes. Step 3 (Cost): NRE claim of $0.42/cell is supplier-caused EOL per MSA §7.1 — historically rejected. Precedent ECO-22104 shows similar change accepted at $0 NRE with 50/50 requal cost split.",
        },
        "critic_review": {
            "review_passed": True,
            "issues": [],
            "citation_audit": {"total_claims": 6, "cited_claims": 6, "faithfulness_score": 1.0},
            "logic_score": 0.92,
            "recommendation": "PUBLISH",
        },
        "is_published": True,
        "latency_seconds": 8.3,
        "total_tokens": 4520,
        "estimated_cost_usd": 0.032,
    }
