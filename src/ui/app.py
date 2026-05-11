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
    FONT, GRAY1, GRAY2, GRAY3, GRAY4, GRAY5, GRAY6, WHITE, BLUE,
    CARD_SHADOW, CARD_RADIUS,
    _section_label, _card_open, _card_close,
)

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ECO-Impact Interpreter",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ──────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
    /* ── Typography ───────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {{
        font-family: {FONT};
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }}

    /* ── Main container ──────────────────────────────────────────── */
    .block-container {{
        padding-top: 2rem !important;
        max-width: 1200px;
    }}

    /* ── Header ──────────────────────────────────────────────────── */
    .app-header {{
        padding: 8px 0 28px 0;
        margin-bottom: 8px;
    }}
    .app-header h1 {{
        font-family: {FONT};
        font-size: 28px;
        font-weight: 700;
        color: {GRAY1};
        margin: 0;
        letter-spacing: -0.025em;
    }}
    .app-header .subtitle {{
        font-family: {FONT};
        color: {GRAY3};
        margin: 6px 0 0 0;
        font-size: 14px;
        font-weight: 400;
        letter-spacing: -0.01em;
    }}

    /* ── Sidebar ─────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {{
        background: {GRAY6};
    }}
    section[data-testid="stSidebar"] > div:first-child {{
        padding-top: 2rem;
    }}
    section[data-testid="stSidebar"] .stMarkdown h3 {{
        font-family: {FONT};
        font-size: 10px;
        font-weight: 600;
        color: {GRAY4};
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }}
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stCheckbox label {{
        font-size: 13px !important;
        color: {GRAY2} !important;
    }}
    section[data-testid="stSidebar"] .stSelectbox label {{
        font-size: 12px !important;
        color: {GRAY3} !important;
    }}

    /* ── Buttons ─────────────────────────────────────────────────── */
    .stButton > button {{
        font-family: {FONT};
        border-radius: 10px;
        font-weight: 500;
        font-size: 14px;
        padding: 8px 22px;
        border: 1px solid {GRAY5};
        background: {WHITE};
        color: {GRAY1};
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }}
    .stButton > button:hover {{
        background: {GRAY6};
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }}
    .stButton > button[kind="primary"] {{
        background: {BLUE};
        color: white;
        border: none;
        box-shadow: 0 1px 3px rgba(0,122,255,0.3);
    }}
    .stButton > button[kind="primary"]:hover {{
        background: #0066d6;
        box-shadow: 0 2px 8px rgba(0,122,255,0.35);
    }}

    /* ── Text area ───────────────────────────────────────────────── */
    .stTextArea textarea {{
        font-family: {FONT};
        border: 1px solid {GRAY5};
        border-radius: 12px;
        font-size: 14px;
        padding: 16px;
        background: {WHITE};
        color: {GRAY1};
        line-height: 1.6;
        transition: border-color 0.2s, box-shadow 0.2s;
    }}
    .stTextArea textarea:focus {{
        border-color: {BLUE};
        box-shadow: 0 0 0 4px rgba(0,122,255,0.08);
    }}
    .stTextArea textarea::placeholder {{
        color: {GRAY4};
    }}

    /* ── Expanders ───────────────────────────────────────────────── */
    .stExpander {{
        border: 1px solid {GRAY5} !important;
        border-radius: 12px !important;
        background: {WHITE} !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }}
    .stExpander summary {{
        font-family: {FONT} !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        color: {GRAY2} !important;
    }}

    /* ── Metrics ─────────────────────────────────────────────────── */
    div[data-testid="stMetricValue"] {{
        font-family: {FONT};
        font-weight: 600;
        font-size: 18px !important;
        color: {GRAY1};
    }}
    div[data-testid="stMetricLabel"] {{
        font-family: {FONT};
        font-size: 10px !important;
        color: {GRAY3};
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 600;
    }}

    /* ── Metadata strip ──────────────────────────────────────────── */
    .meta-strip {{
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 12px 20px;
        background: {WHITE};
        border: 1px solid {GRAY5};
        border-radius: {CARD_RADIUS};
        box-shadow: {CARD_SHADOW};
        flex-wrap: wrap;
    }}
    .meta-strip .meta-item {{
        font-family: {FONT};
        font-size: 13px;
        color: {GRAY2};
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .meta-strip .meta-item .label {{
        font-size: 10px;
        font-weight: 600;
        color: {GRAY4};
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }}
    .meta-strip .meta-sep {{
        width: 1px;
        height: 20px;
        background: {GRAY5};
    }}

    /* ── Hide Streamlit chrome ───────────────────────────────────── */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header[data-testid="stHeader"] {{background: transparent; height: 0;}}

    /* ── Spacing ─────────────────────────────────────────────────── */
    div[data-testid="stVerticalBlock"] > div:has(> div.stMarkdown) {{ gap: 0.35rem; }}
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("""
<div class="app-header">
    <h1>ECO-Impact Interpreter</h1>
    <p class="subtitle">Eng2Biz Decision Cockpit for Global Supply Managers</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Mode")

    mode = st.radio(
        "Mode",
        ["Live Analysis (API)", "Demo Mode (Sample Data)"],
        index=1,
        help="Demo mode uses pre-computed results without API calls",
        label_visibility="collapsed",
    )

    st.markdown("### Pipeline")

    enable_critique = st.checkbox("Self-Critique", value=True)
    enable_citations = st.checkbox("Citations", value=True)

    st.markdown("### Sample ECOs")

    sample_ecos = {
        "CASE-01: Battery Binder": (
            "ECO-24817: Change battery cathode binder from PVDF-A to PVDF-B, "
            "effective W38. Supplier claims +$0.42/cell NRE and 5-week requal. "
            "Reason: PVDF-A upstream supplier exiting market Q3."
        ),
        "CASE-02: Display IC EOL": (
            "PCN-2025-0342: Display driver IC (P/N: DD-IC-7820A) end-of-life notice. "
            "Last time buy deadline: 2025-08-15. Recommended replacement: DD-IC-7821B. "
            "Pin-compatible but requires firmware update. Supplier: BOE Technology."
        ),
        "CASE-03: Anodize Yield": (
            "YIELD EXCURSION REPORT: Batch #W37-ENC-042. Anodize color match "
            "failure rate spiked to 12% (normal: 2-3%). Root cause: Type II anodize "
            "bath chemistry drift. Affects P/N: ENC-88421-A. Supplier: Lens Technology."
        ),
        "CASE-04: Solder Fatigue": (
            "FA-2025-0089: Field return analysis -- solder joint fatigue on U12 (BGA-256, "
            "0.5mm pitch). 23 units returned from 50K shipment. Failure mode: crack "
            "propagation at corner balls after 800 thermal cycles. Supplier: Jabil."
        ),
        "CASE-05: EVT Exit": (
            "EVT EXIT READOUT: Product Alpha, Build W35. Marginal CTQs identified: "
            "(1) Battery impedance 15% above target at -10C, (2) Display brightness "
            "non-uniformity at 8% (spec: <=5%), (3) Enclosure gap at antenna band "
            "0.12mm (spec: <=0.10mm). DVT entry decision pending."
        ),
        "FAIL-01: Vague (Refuse)": (
            "We got an update from Vendor A on the battery issue. They're saying "
            "the yield problem is the film supplier's fault, not theirs. "
            "Recommend holding the PO."
        ),
    }

    selected_sample = st.selectbox(
        "Select a case",
        list(sample_ecos.keys()),
        label_visibility="collapsed",
    )
    if st.button("Load Sample", use_container_width=True):
        st.session_state["input_text"] = sample_ecos[selected_sample]

    st.markdown("")
    st.markdown(
        f'<div style="font-family:{FONT};font-size:11px;color:{GRAY4};'
        f'padding-top:12px;border-top:1px solid {GRAY5};">'
        f'v1.0.0 &middot; JHU Carey BU.330.760.T1<br>'
        f'All data is 100% synthetic</div>',
        unsafe_allow_html=True,
    )

# ─── Input Area ──────────────────────────────────────────────────────────────

st.markdown(_section_label("Input"), unsafe_allow_html=True)

input_text = st.text_area(
    "Paste ECO, PCN, yield report, DFM memo, or FA report:",
    value=st.session_state.get("input_text", ""),
    height=130,
    placeholder="Paste an ECO, PCN, yield report, DFM memo, or FA report here...",
    label_visibility="collapsed",
)

col_btn1, col_btn2, _ = st.columns([1, 1, 5])
with col_btn1:
    analyze_btn = st.button("Analyze", type="primary", use_container_width=True)
with col_btn2:
    clear_btn = st.button("Clear", use_container_width=True)

if clear_btn:
    st.session_state["input_text"] = ""
    st.session_state.pop("result", None)
    st.rerun()

# ─── Demo Result Generator ──────────────────────────────────────────────────

def _generate_demo_result(text: str) -> dict:
    """Generate a simulated pipeline result for demo mode."""
    refusal_keywords = ["vendor a", "vague", "the issue", "they're saying"]
    is_refusal = sum(1 for kw in refusal_keywords if kw in text.lower()) >= 2

    if is_refusal:
        return {
            "case_id": "DEMO",
            "input_text": text,
            "parsed_artifact": {
                "artifact_type": "OTHER", "commodity": "OTHER",
                "parse_confidence": 0.25,
                "ambiguities": ["Vague supplier reference", "No artifact ID", "No part number"],
                "raw_text": text,
            },
            "retrieved_context": {"glossary": [], "eco_precedents": [], "msa_clauses": []},
            "refusal": {
                "is_refusal": True,
                "reason": "Insufficient information to generate a reliable GSM Brief. Parse confidence: 0.25",
                "missing_info": [
                    "Supplier ID or MSA number -- 'Vendor A' is not a unique identifier",
                    "Part number or commodity specification",
                    "Artifact reference (ECO#, PCN#, FA#)",
                    "Supporting data for the yield claim",
                ],
                "required_clarifications": [
                    "Provide the supplier's MSA number or full legal name",
                    "Provide the specific part number and commodity",
                    "Provide the ECO or FA number for this issue",
                    "Provide test data or FA report supporting the blame claim",
                ],
            },
            "brief": None,
            "is_published": False,
            "latency_seconds": 1.5, "total_tokens": 0, "estimated_cost_usd": 0.0,
        }

    return {
        "case_id": "DEMO",
        "input_text": text,
        "parsed_artifact": {
            "artifact_id": "ECO-DEMO", "artifact_type": "ECO",
            "commodity": "battery", "supplier_id": "SUP-001",
            "part_number": "BAT-001-A", "parse_confidence": 0.88,
            "ambiguities": [], "raw_text": text,
            "entities": {"materials": [], "tolerances": [], "processes": []},
        },
        "retrieved_context": {
            "glossary": [
                {"id": "G051", "source": "glossary", "content": "PVDF (Polyvinylidene Fluoride): Binder material for electrode coatings. Commercial Impact: PVDF grade changes may require slurry reformulation and coating line validation -- 3-6 week requal.", "score": 0.92, "metadata": {"term": "PVDF", "category": "Battery/Cell"}},
                {"id": "G059", "source": "glossary", "content": "NRE (Non-Recurring Engineering): One-time engineering/tooling cost. Commercial Impact: NRE is amortized over production volume.", "score": 0.87, "metadata": {"term": "NRE", "category": "Battery/Cell"}},
                {"id": "G060", "source": "glossary", "content": "Requal (Requalification): Re-testing and re-approval of changed component. Commercial Impact: Requal typically 4-8 weeks for mechanical, 8-16 weeks for battery/safety-critical.", "score": 0.85, "metadata": {"term": "Requal", "category": "Battery/Cell"}},
            ],
            "eco_precedents": [
                {"id": "E015", "source": "eco_corpus", "content": "ECO-22104 (battery): Changed cathode active material supplier. Impact: +$0.18/cell, 6-week requal. Resolution: Accepted after negotiating NRE split 50/50.", "score": 0.89, "metadata": {"commodity": "battery", "cost_trend": "UP"}},
            ],
            "msa_clauses": [
                {"id": "M07", "source": "msa", "content": "MSA 7.1 Tooling and NRE: Supplier-caused EOL changes are supplier-funded. Buyer-initiated changes split NRE per volume tier.", "score": 0.91, "metadata": {"section": "7.0", "title": "Tooling Ownership"}},
            ],
        },
        "brief": {
            "translation": {
                "en": "Supplier is changing a key cathode binder material (PVDF-A to PVDF-B) because PVDF-A's own supplier is exiting the market. They are requesting a $0.42/cell premium and 5 weeks for re-qualification.",
            },
            "cost_impact": {
                "trend": "UP",
                "unit_price_delta": "+$0.42/cell (claimed NRE)",
                "nre_estimate": "$0.42/cell x 12M units = ~$5.0M claimed",
                "reasoning": "Per MSA 7.1 [M07], supplier-caused EOL changes are supplier-funded -- claim is likely rejectable. Precedent ECO-22104 [E015]: identical scenario, $0 NRE accepted.",
                "total_exposure": "$5.0M claimed, $0 expected after negotiation",
            },
            "schedule_impact": {
                "lead_time_delta_weeks": 5,
                "requal_needed": True,
                "critical_path_risk": "5-week requal from W38 to complete W43. If MP >= W44, schedule intact.",
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
                {"action": "Reject NRE claim in writing citing MSA 7.1; supplier-caused EOL = supplier cost", "owner": "Sr. GSM", "confidence": 0.92, "requires_approval_from": None, "citation_refs": ["M07", "E015"]},
                {"action": "Kick off 5-week requal clock at W38; request PVDF-B data package by W36", "owner": "GSM (you)", "confidence": 0.88, "requires_approval_from": None, "citation_refs": ["G051"]},
                {"action": "Validate MP date buffer vs W43 re-qual completion with OPM", "owner": "OPM", "confidence": 0.85, "requires_approval_from": None, "citation_refs": []},
            ],
            "citations_used": {"glossary": ["G051", "G059", "G060"], "eco_precedents": ["E015"], "msa_clauses": ["M07"]},
            "overall_confidence": 0.89,
            "chain_of_thought": "Step 1 (Physical): PVDF binder change affects electrode coating adhesion and slurry viscosity. Step 2 (Process): Requires slurry reformulation, coating line parameter adjustment, and formation cycling validation. 5-week requal is reasonable. Step 3 (Cost): NRE claim of $0.42/cell is supplier-caused EOL per MSA 7.1 -- historically rejected.",
        },
        "critic_review": {
            "review_passed": True, "issues": [],
            "citation_audit": {"total_claims": 6, "cited_claims": 6, "faithfulness_score": 1.0},
            "logic_score": 0.92, "recommendation": "PUBLISH",
        },
        "is_published": True,
        "latency_seconds": 8.3, "total_tokens": 4520, "estimated_cost_usd": 0.032,
    }

# ─── Analysis ────────────────────────────────────────────────────────────────

if analyze_btn and input_text.strip():
    if mode == "Live Analysis (API)":
        with st.spinner("Running Eng2Biz pipeline..."):
            try:
                from src.core.pipeline import Eng2BizPipeline
                pipeline = Eng2BizPipeline()
                result = pipeline.run(input_text)
                st.session_state["result"] = result.model_dump()
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.info("Make sure your API key is configured in .env and RAG indices are built.")
                st.stop()
    else:
        with st.spinner("Simulating analysis..."):
            time.sleep(1.2)
            st.session_state["result"] = _generate_demo_result(input_text)

# ─── Display Results ─────────────────────────────────────────────────────────

if "result" in st.session_state:
    result = st.session_state["result"]

    # Spacing
    st.markdown(f'<div style="height:28px;"></div>', unsafe_allow_html=True)

    if result.get("refusal"):
        render_refusal(result["refusal"])

    elif result.get("brief"):
        brief = result["brief"]
        parsed = result.get("parsed_artifact", {})
        context = result.get("retrieved_context", {})
        review = result.get("critic_review")

        # ── Metadata strip ───────────────────────────────────────────
        atype = parsed.get("artifact_type", "ECO")
        artifact_id = parsed.get("artifact_id", "N/A")
        commodity = parsed.get("commodity", "N/A")
        conf = brief.get("overall_confidence", 0)
        is_pub = result.get("is_published", False)

        pub_color = "#34c759" if is_pub else AMBER
        pub_text = "Published" if is_pub else "Pending"

        st.markdown(f"""
        <div class="meta-strip">
            <div class="meta-item">
                <span style="background:{BLUE};color:white;padding:3px 12px;
                             border-radius:100px;font-weight:500;font-size:12px;">{atype}</span>
            </div>
            <div class="meta-sep"></div>
            <div class="meta-item">
                <span class="label">ID</span>
                <span style="font-weight:500;">{artifact_id}</span>
            </div>
            <div class="meta-sep"></div>
            <div class="meta-item">
                <span class="label">Commodity</span>
                <span>{commodity}</span>
            </div>
            <div class="meta-sep"></div>
            <div class="meta-item">
                <span class="label">Confidence</span>
                {render_confidence_badge(conf)}
            </div>
            <div class="meta-sep"></div>
            <div class="meta-item">
                <span style="color:{pub_color};font-weight:600;font-size:13px;">{pub_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f'<div style="height:20px;"></div>', unsafe_allow_html=True)

        # ── Two-column layout ────────────────────────────────────────
        left_col, right_col = st.columns([1, 1], gap="large")

        with left_col:
            glossary_matches = context.get("glossary", [])
            render_engineering_context(
                result.get("input_text", input_text),
                glossary_matches,
            )

            if enable_citations:
                eco_precedents = context.get("eco_precedents", [])
                msa_clauses = context.get("msa_clauses", [])

                if eco_precedents:
                    st.markdown("", unsafe_allow_html=True)
                    st.markdown(_section_label("ECO Precedents"), unsafe_allow_html=True)
                    for chunk in eco_precedents:
                        cid = chunk.get("id", "") if isinstance(chunk, dict) else ""
                        content = chunk.get("content", "") if isinstance(chunk, dict) else ""
                        from src.ui.components import render_citation_chip
                        render_citation_chip(cid, content)

                if msa_clauses:
                    st.markdown("", unsafe_allow_html=True)
                    st.markdown(_section_label("MSA Clauses"), unsafe_allow_html=True)
                    for chunk in msa_clauses:
                        cid = chunk.get("id", "") if isinstance(chunk, dict) else ""
                        content = chunk.get("content", "") if isinstance(chunk, dict) else ""
                        from src.ui.components import render_citation_chip
                        render_citation_chip(cid, content)

        with right_col:
            render_gsm_brief(brief)

        # ── Score dashboard ──────────────────────────────────────────
        st.markdown(f'<div style="height:24px;"></div>', unsafe_allow_html=True)
        st.markdown(_section_label("Quality Scores"), unsafe_allow_html=True)
        render_score_dashboard(brief, review)

        # ── Pipeline metrics ─────────────────────────────────────────
        st.markdown(f'<div style="height:16px;"></div>', unsafe_allow_html=True)
        with st.expander("Pipeline Metrics"):
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

        with st.expander("Raw JSON"):
            st.json(brief)

elif analyze_btn:
    st.warning("Please enter an engineering artifact to analyze.")
