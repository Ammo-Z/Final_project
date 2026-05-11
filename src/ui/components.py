"""Reusable Streamlit UI components for the ECO-Impact Interpreter."""

from __future__ import annotations
import streamlit as st
from typing import Optional


# ─── Shared Style Tokens ────────────────────────────────────────────────────

FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', 'Helvetica Neue', Arial, sans-serif"
MONO = "'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace"

# Apple system colors
BLUE = "#007aff"
GREEN = "#34c759"
AMBER = "#ff9f0a"
RED = "#ff3b30"
GRAY1 = "#1d1d1f"   # primary text
GRAY2 = "#48484a"   # secondary text
GRAY3 = "#86868b"   # tertiary / labels
GRAY4 = "#aeaeb2"   # placeholder
GRAY5 = "#d1d1d6"   # borders
GRAY6 = "#f2f2f7"   # backgrounds
WHITE = "#ffffff"

CARD_SHADOW = "0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)"
CARD_SHADOW_HOVER = "0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)"
CARD_RADIUS = "14px"


def _section_label(text: str) -> str:
    """Return HTML for a small uppercase section label."""
    return (
        f'<p style="font-family:{FONT};font-size:11px;font-weight:600;'
        f'color:{GRAY3};letter-spacing:0.06em;text-transform:uppercase;'
        f'margin:0 0 6px 0;">{text}</p>'
    )


def _card_open(padding: str = "20px 24px", extra: str = "") -> str:
    return (
        f'<div style="background:{WHITE};border:1px solid {GRAY5};'
        f'border-radius:{CARD_RADIUS};padding:{padding};'
        f'box-shadow:{CARD_SHADOW};{extra}">'
    )


def _card_close() -> str:
    return '</div>'


def _thin_divider() -> str:
    return f'<div style="height:1px;background:{GRAY5};margin:16px 0;opacity:0.6;"></div>'


def render_confidence_badge(confidence: float) -> str:
    """Render a minimal confidence pill."""
    if confidence >= 0.9:
        bg = GREEN
    elif confidence >= 0.7:
        bg = AMBER
    else:
        bg = RED
    return (
        f'<span style="display:inline-block;background:{bg};color:{WHITE};'
        f'padding:4px 14px;border-radius:100px;font-family:{FONT};'
        f'font-weight:500;font-size:13px;letter-spacing:0.01em;">'
        f'{confidence:.0%}</span>'
    )


def render_cost_trend_badge(trend: str) -> str:
    """Render cost trend indicator."""
    colors = {"UP": RED, "DOWN": GREEN, "NEUTRAL": GRAY3}
    arrows = {"UP": "^", "DOWN": "v", "NEUTRAL": "-"}
    c = colors.get(trend, GRAY3)
    arrow = arrows.get(trend, "-")
    return (
        f'<span style="display:inline-flex;align-items:center;gap:6px;'
        f'background:{c}15;color:{c};padding:4px 12px;border-radius:8px;'
        f'font-family:{FONT};font-weight:600;font-size:13px;">'
        f'{trend}</span>'
    )


def render_risk_badge(level: str) -> str:
    """Render risk level pill."""
    colors = {"HIGH": RED, "MEDIUM": AMBER, "LOW": GREEN}
    c = colors.get(level, GRAY3)
    return (
        f'<span style="display:inline-block;background:{c}15;color:{c};'
        f'padding:4px 14px;border-radius:100px;font-family:{FONT};'
        f'font-weight:600;font-size:13px;">{level}</span>'
    )


def render_citation_chip(ref_id: str, content: str) -> None:
    """Render a citation chip with expandable content."""
    source_colors = {"G": BLUE, "E": "#af52de", "M": AMBER}
    color = source_colors.get(ref_id[0], GRAY3) if ref_id else GRAY3
    with st.expander(ref_id, expanded=False):
        st.markdown(
            f'<div style="background:{GRAY6};padding:14px 16px;'
            f'border-left:3px solid {color};border-radius:0 8px 8px 0;'
            f'font-family:{FONT};font-size:13px;color:{GRAY2};line-height:1.65;">'
            f'{content}</div>',
            unsafe_allow_html=True,
        )


def render_action_card(action: dict, index: int) -> None:
    """Render a recommended action card."""
    confidence = action.get("confidence", 0)
    if confidence >= 0.8:
        accent = GREEN
    elif confidence >= 0.6:
        accent = AMBER
    else:
        accent = RED

    st.markdown(f"""
    <div style="background:{GRAY6};padding:14px 18px;border-radius:10px;
                margin:6px 0;border-left:3px solid {accent};
                transition:background 0.15s ease;">
        <div style="font-family:{FONT};font-weight:500;color:{GRAY1};
                    font-size:13.5px;line-height:1.5;">
            <span style="color:{GRAY3};font-weight:600;margin-right:6px;">{index + 1}.</span>
            {action.get('action', '')}
        </div>
        <div style="margin-top:8px;display:flex;align-items:center;gap:10px;
                    font-family:{FONT};font-size:12px;color:{GRAY3};">
            <span style="background:{WHITE};border:1px solid {GRAY5};
                         padding:2px 10px;border-radius:6px;">{action.get('owner', 'GSM')}</span>
            <span style="background:{accent}18;color:{accent};
                         padding:2px 10px;border-radius:6px;font-weight:600;">
                {confidence:.0%}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_engineering_context(raw_text: str, glossary_matches: list) -> None:
    """Render the left pane — engineering source text with highlighted terms."""
    highlight_map = {}
    for chunk in glossary_matches:
        metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else getattr(chunk, "metadata", {})
        term = metadata.get("term", "")
        if term:
            content = chunk.get("content", "") if isinstance(chunk, dict) else getattr(chunk, "content", "")
            highlight_map[term.lower()] = content

    st.markdown(_section_label("Source Artifact"), unsafe_allow_html=True)

    display_text = raw_text
    for term in sorted(highlight_map.keys(), key=len, reverse=True):
        if term.lower() in display_text.lower():
            display_text = display_text.replace(
                term,
                f'<mark style="background:rgba(0,122,255,0.1);padding:1px 4px;'
                f'border-radius:4px;border-bottom:2px solid {BLUE};cursor:help;" '
                f'title="{highlight_map[term][:120]}">{term}</mark>',
            )

    st.markdown(
        f'{_card_open("20px 22px")}'
        f'<div style="font-family:{MONO};font-size:13px;line-height:1.85;'
        f'color:{GRAY1};white-space:pre-wrap;word-break:break-word;">'
        f'{display_text}</div>{_card_close()}',
        unsafe_allow_html=True,
    )

    if glossary_matches:
        st.markdown("", unsafe_allow_html=True)
        st.markdown(_section_label("Referenced Terms"), unsafe_allow_html=True)
        for chunk in glossary_matches:
            cid = chunk.get("id", "") if isinstance(chunk, dict) else getattr(chunk, "id", "")
            content = chunk.get("content", "") if isinstance(chunk, dict) else getattr(chunk, "content", "")
            render_citation_chip(cid, content)


def render_gsm_brief(brief: dict) -> None:
    """Render the right pane GSM Brief in a single card."""
    st.markdown(_section_label("Decision Brief"), unsafe_allow_html=True)

    # Build the entire brief inside one card
    html_parts = [_card_open("24px 26px")]

    # Translation
    translation = brief.get("translation", {})
    html_parts.append(
        f'<div style="font-family:{FONT};font-size:11px;font-weight:600;'
        f'color:{GRAY3};letter-spacing:0.06em;text-transform:uppercase;'
        f'margin-bottom:8px;">Plain-Language Summary</div>'
        f'<div style="font-family:{FONT};font-size:14.5px;color:{GRAY1};'
        f'line-height:1.6;font-weight:400;">{translation.get("en", "")}</div>'
    )
    html_parts.append(_thin_divider())

    # Cost Impact
    cost = brief.get("cost_impact", {})
    trend_color = {"UP": RED, "DOWN": GREEN, "NEUTRAL": GRAY3}.get(cost.get("trend", "NEUTRAL"), GRAY3)
    html_parts.append(
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-family:{FONT};font-size:11px;font-weight:600;'
        f'color:{GRAY3};letter-spacing:0.06em;text-transform:uppercase;">Cost Impact</span>'
        f'<span style="background:{trend_color}12;color:{trend_color};padding:3px 12px;'
        f'border-radius:6px;font-family:{FONT};font-weight:600;font-size:12px;">'
        f'{cost.get("trend", "NEUTRAL")}</span></div>'
    )
    if cost.get("reasoning"):
        html_parts.append(
            f'<div style="font-family:{FONT};font-size:13.5px;color:{GRAY2};'
            f'line-height:1.55;margin-top:8px;">{cost["reasoning"]}</div>'
        )
    html_parts.append(_thin_divider())

    # Schedule Impact
    schedule = brief.get("schedule_impact", {})
    html_parts.append(
        f'<div style="font-family:{FONT};font-size:11px;font-weight:600;'
        f'color:{GRAY3};letter-spacing:0.06em;text-transform:uppercase;'
        f'margin-bottom:8px;">Schedule Impact</div>'
        f'<div style="display:flex;gap:20px;font-family:{FONT};font-size:13.5px;color:{GRAY1};">'
        f'<div>Lead time delta <strong>{schedule.get("lead_time_delta_weeks", 0)}w</strong></div>'
        f'<div>Requal <strong>{"Yes" if schedule.get("requal_needed") else "No"}</strong></div>'
        f'</div>'
    )
    if schedule.get("critical_path_risk"):
        html_parts.append(
            f'<div style="font-family:{FONT};font-size:13px;color:{GRAY2};'
            f'line-height:1.55;margin-top:6px;">{schedule["critical_path_risk"]}</div>'
        )
    html_parts.append(_thin_divider())

    # Risk Assessment
    risk = brief.get("risk_assessment", {})
    risk_color = {"HIGH": RED, "MEDIUM": AMBER, "LOW": GREEN}.get(risk.get("level", "LOW"), GRAY3)
    html_parts.append(
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-family:{FONT};font-size:11px;font-weight:600;'
        f'color:{GRAY3};letter-spacing:0.06em;text-transform:uppercase;">Risk</span>'
        f'<span style="background:{risk_color}12;color:{risk_color};padding:3px 12px;'
        f'border-radius:6px;font-family:{FONT};font-weight:600;font-size:12px;">'
        f'{risk.get("level", "LOW")}</span></div>'
    )
    for factor in risk.get("factors", []):
        html_parts.append(
            f'<div style="font-family:{FONT};font-size:13px;color:{GRAY2};'
            f'line-height:1.5;margin-top:4px;padding-left:2px;">- {factor}</div>'
        )

    html_parts.append(_card_close())
    st.markdown("\n".join(html_parts), unsafe_allow_html=True)

    # Recommended Actions — separate section below the card
    st.markdown("", unsafe_allow_html=True)
    st.markdown(_section_label("Recommended Actions"), unsafe_allow_html=True)
    for i, action in enumerate(brief.get("recommended_actions", [])):
        render_action_card(action, i)


def render_refusal(refusal: dict) -> None:
    """Render a refusal response."""
    st.markdown(
        f'{_card_open("20px 24px", f"border-color:{RED};border-left:4px solid {RED};")}'
        f'<div style="font-family:{FONT};font-weight:600;color:{RED};'
        f'font-size:15px;margin-bottom:10px;">Brief Withheld</div>'
        f'<div style="font-family:{FONT};font-size:14px;color:{GRAY1};'
        f'line-height:1.55;">{refusal.get("reason", "")}</div>'
        f'{_card_close()}',
        unsafe_allow_html=True,
    )

    missing = refusal.get("missing_info", [])
    if missing:
        st.markdown("", unsafe_allow_html=True)
        st.markdown(_section_label("Issues Detected"), unsafe_allow_html=True)
        for item in missing:
            st.markdown(
                f'<div style="font-family:{FONT};font-size:13.5px;color:{GRAY2};'
                f'padding:4px 0;line-height:1.5;">- {item}</div>',
                unsafe_allow_html=True,
            )

    clarifications = refusal.get("required_clarifications", [])
    if clarifications:
        st.markdown("", unsafe_allow_html=True)
        st.markdown(_section_label("Required Information"), unsafe_allow_html=True)
        for item in clarifications:
            st.markdown(
                f'<div style="font-family:{FONT};font-size:13.5px;color:{GRAY2};'
                f'padding:4px 0;line-height:1.5;">- {item}</div>',
                unsafe_allow_html=True,
            )


def render_score_dashboard(brief: dict, review: Optional[dict] = None) -> None:
    """Render the scoring dashboard as a horizontal card."""
    metrics = [
        ("Translation", brief.get("overall_confidence", 0) * 5),
        ("Completeness", brief.get("overall_confidence", 0) * 4.8),
        ("Citations", 5.0 if review and review.get("citation_audit", {}).get("faithfulness_score", 0) >= 0.95 else 4.0),
        ("Actions", min(len(brief.get("recommended_actions", [])) * 1.5, 5.0)),
        ("Overall", brief.get("overall_confidence", 0) * 5),
    ]

    cells = []
    for label, score in metrics:
        if score >= 4.0:
            color = GREEN
        elif score >= 3.0:
            color = AMBER
        else:
            color = RED
        cells.append(
            f'<div style="flex:1;text-align:center;padding:12px 0;">'
            f'<div style="font-size:10px;font-weight:600;color:{GRAY3};'
            f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px;">{label}</div>'
            f'<div style="font-size:22px;font-weight:600;color:{color};'
            f'font-family:{FONT};">{score:.1f}</div>'
            f'<div style="font-size:10px;color:{GRAY4};margin-top:2px;">/ 5.0</div>'
            f'</div>'
        )

    divider = f'<div style="width:1px;background:{GRAY5};margin:8px 0;opacity:0.5;"></div>'
    inner = divider.join(cells)

    st.markdown(
        f'{_card_open("8px 16px")}'
        f'<div style="display:flex;align-items:stretch;">{inner}</div>'
        f'{_card_close()}',
        unsafe_allow_html=True,
    )
