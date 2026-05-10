"""Reusable Streamlit UI components for the ECO-Impact Interpreter."""

from __future__ import annotations
import json
import streamlit as st
from typing import Optional


def render_confidence_badge(confidence: float) -> str:
    """Render a colored confidence badge."""
    if confidence >= 0.9:
        color = "#22c55e"  # green
    elif confidence >= 0.7:
        color = "#f59e0b"  # amber
    else:
        color = "#ef4444"  # red
    return f'<span style="background:{color};color:white;padding:2px 10px;border-radius:12px;font-weight:600;font-size:0.85em;">Conf {confidence:.2f}</span>'


def render_cost_trend_badge(trend: str) -> str:
    """Render cost trend with color indicator."""
    colors = {"UP": "#ef4444", "DOWN": "#22c55e", "NEUTRAL": "#6b7280"}
    icons = {"UP": "▲", "DOWN": "▼", "NEUTRAL": "●"}
    c = colors.get(trend, "#6b7280")
    i = icons.get(trend, "●")
    return f'<span style="color:{c};font-weight:700;font-size:1.1em;">{i} {trend}</span>'


def render_risk_badge(level: str) -> str:
    """Render risk level badge."""
    colors = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}
    c = colors.get(level, "#6b7280")
    return f'<span style="background:{c};color:white;padding:2px 10px;border-radius:12px;font-weight:600;">RISK: {level}</span>'


def render_citation_chip(ref_id: str, content: str) -> None:
    """Render a clickable citation chip with expandable content."""
    source_colors = {"G": "#3b82f6", "E": "#8b5cf6", "M": "#f59e0b"}
    color = source_colors.get(ref_id[0], "#6b7280")
    with st.expander(f"📎 {ref_id}", expanded=False):
        st.markdown(
            f'<div style="background:#f8f9fa;padding:12px;border-left:3px solid {color};border-radius:4px;font-size:0.9em;">{content}</div>',
            unsafe_allow_html=True,
        )


def render_action_card(action: dict, index: int) -> None:
    """Render a recommended action card."""
    confidence = action.get("confidence", 0)
    bar_color = "#22c55e" if confidence >= 0.8 else "#f59e0b" if confidence >= 0.6 else "#ef4444"
    st.markdown(f"""
    <div style="background:#f8f9fa;padding:12px 16px;border-radius:8px;margin:8px 0;border-left:4px solid {bar_color};">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-weight:600;">❶ {action.get('action', '')}</span>
        </div>
        <div style="margin-top:6px;font-size:0.85em;color:#6b7280;">
            → {action.get('owner', 'GSM')} &nbsp;&nbsp;
            <span style="background:{bar_color};color:white;padding:1px 8px;border-radius:8px;">{confidence:.2f}</span>
        </div>
    </div>
    """.replace("❶", f"❶❷❸❹❺"[index] if index < 5 else f"#{index+1}"), unsafe_allow_html=True)


def render_engineering_context(raw_text: str, glossary_matches: list) -> None:
    """Render the left pane with highlighted technical terms."""
    # Build term highlight map
    highlight_map = {}
    for chunk in glossary_matches:
        metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else getattr(chunk, "metadata", {})
        term = metadata.get("term", "")
        if term:
            content = chunk.get("content", "") if isinstance(chunk, dict) else getattr(chunk, "content", "")
            highlight_map[term.lower()] = content

    st.markdown("### ENGINEERING ARTIFACT INPUT / 原始工程文本")

    # Display raw text with term highlights
    display_text = raw_text
    for term in sorted(highlight_map.keys(), key=len, reverse=True):
        if term.lower() in display_text.lower():
            display_text = display_text.replace(
                term, f'<span style="background:#dbeafe;padding:1px 4px;border-radius:3px;cursor:help;" title="{highlight_map[term][:100]}...">{term}</span>'
            )

    st.markdown(
        f'<div style="background:#f1f5f9;padding:16px;border-radius:8px;font-family:monospace;line-height:1.8;font-size:0.95em;">{display_text}</div>',
        unsafe_allow_html=True,
    )

    # Citation chips
    if glossary_matches:
        st.markdown("**Referenced Terms:**")
        for chunk in glossary_matches:
            cid = chunk.get("id", "") if isinstance(chunk, dict) else getattr(chunk, "id", "")
            content = chunk.get("content", "") if isinstance(chunk, dict) else getattr(chunk, "content", "")
            render_citation_chip(cid, content)


def render_gsm_brief(brief: dict) -> None:
    """Render the right pane GSM Brief output."""
    st.markdown("### GSM BRIEF OUTPUT / 商业决策简报")

    # Translation
    translation = brief.get("translation", {})
    st.markdown("**TRANSLATION**")
    st.markdown(translation.get("en", ""))
    if translation.get("zh"):
        st.markdown(f'*{translation.get("zh")}*')

    st.divider()

    # Cost Impact
    cost = brief.get("cost_impact", {})
    st.markdown("**COST IMPACT**")
    st.markdown(render_cost_trend_badge(cost.get("trend", "NEUTRAL")), unsafe_allow_html=True)
    if cost.get("reasoning"):
        st.markdown(cost["reasoning"])

    st.divider()

    # Schedule Impact
    schedule = brief.get("schedule_impact", {})
    st.markdown("**SCHEDULE IMPACT**")
    st.markdown(
        f"Lead time delta: **{schedule.get('lead_time_delta_weeks', 0)} weeks** | "
        f"Requal needed: **{'Yes' if schedule.get('requal_needed') else 'No'}**"
    )
    if schedule.get("critical_path_risk"):
        st.markdown(schedule["critical_path_risk"])

    st.divider()

    # Risk Assessment
    risk = brief.get("risk_assessment", {})
    st.markdown("**RISK ASSESSMENT**")
    st.markdown(render_risk_badge(risk.get("level", "LOW")), unsafe_allow_html=True)
    for factor in risk.get("factors", []):
        st.markdown(f"- {factor}")

    st.divider()

    # Recommended Actions
    st.markdown("**RECOMMENDED ACTIONS**")
    for i, action in enumerate(brief.get("recommended_actions", [])):
        render_action_card(action, i)


def render_refusal(refusal: dict) -> None:
    """Render a refusal response."""
    st.error("⚠️ System Response: REFUSAL — Brief Withheld")
    st.markdown(f"**Reason:** {refusal.get('reason', '')}")

    missing = refusal.get("missing_info", [])
    if missing:
        st.markdown("**Issues detected:**")
        for item in missing:
            st.markdown(f"- {item}")

    clarifications = refusal.get("required_clarifications", [])
    if clarifications:
        st.markdown("**Please provide:**")
        for item in clarifications:
            st.markdown(f"- {item}")


def render_score_dashboard(brief: dict, review: Optional[dict] = None) -> None:
    """Render the scoring dashboard at the bottom."""
    cols = st.columns(5)
    metrics = [
        ("TRANSLATION", brief.get("overall_confidence", 0) * 5),
        ("COMPLETE", brief.get("overall_confidence", 0) * 4.8),
        ("CITATIONS", 5.0 if review and review.get("citation_audit", {}).get("faithfulness_score", 0) >= 0.95 else 4.0),
        ("ACTIONS", min(len(brief.get("recommended_actions", [])) * 1.5, 5.0)),
        ("OVERALL", brief.get("overall_confidence", 0) * 5),
    ]
    for col, (label, score) in zip(cols, metrics):
        with col:
            color = "#22c55e" if score >= 4.0 else "#f59e0b" if score >= 3.0 else "#ef4444"
            st.markdown(
                f'<div style="text-align:center;"><div style="font-size:0.75em;color:#6b7280;">{label}</div>'
                f'<div style="font-size:1.5em;font-weight:700;color:{color};">{score:.1f}</div></div>',
                unsafe_allow_html=True,
            )
