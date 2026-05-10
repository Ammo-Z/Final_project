"""Pydantic data models for ECO-Impact Interpreter pipeline."""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────────────────────

class ArtifactType(str, Enum):
    ECO = "ECO"
    PCN = "PCN"
    YIELD = "YIELD"
    DFM = "DFM"
    FA = "FA"
    EVT = "EVT"
    OTHER = "OTHER"


class Commodity(str, Enum):
    BATTERY = "battery"
    DISPLAY = "display"
    ENCLOSURE = "enclosure"
    PCBA = "PCBA"
    MECHANICAL = "mechanical"
    THERMAL = "thermal"
    CONNECTOR = "connector"
    OTHER = "OTHER"


class CostTrend(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    NEUTRAL = "NEUTRAL"


class RiskLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ReviewRecommendation(str, Enum):
    PUBLISH = "PUBLISH"
    REVISE = "REVISE"
    REFUSAL_OVERRIDE = "REFUSAL_OVERRIDE"


# ─── Parser Output ───────────────────────────────────────────────────────────

class MaterialEntity(BaseModel):
    name: str
    spec: Optional[str] = None
    change_type: str = "modify"  # add | remove | modify


class ToleranceEntity(BaseModel):
    dimension: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    unit: str = "mm"


class ProcessEntity(BaseModel):
    name: str
    change_type: str = "modify"
    detail: Optional[str] = None


class SpecEntity(BaseModel):
    standard: str
    requirement: Optional[str] = None


class CostSignal(BaseModel):
    type: str  # NRE | unit_price | tooling
    value: Optional[str] = None
    currency: str = "USD"


class ScheduleSignal(BaseModel):
    type: str  # lead_time | effectivity | requal
    value: Optional[str] = None
    unit: str = "weeks"


class RiskIndicator(BaseModel):
    type: str
    severity: str = "medium"
    detail: Optional[str] = None


class ParsedEntities(BaseModel):
    materials: list[MaterialEntity] = Field(default_factory=list)
    tolerances: list[ToleranceEntity] = Field(default_factory=list)
    processes: list[ProcessEntity] = Field(default_factory=list)
    specifications: list[SpecEntity] = Field(default_factory=list)
    cost_signals: list[CostSignal] = Field(default_factory=list)
    schedule_signals: list[ScheduleSignal] = Field(default_factory=list)
    risk_indicators: list[RiskIndicator] = Field(default_factory=list)


class ParsedArtifact(BaseModel):
    """Output of the Parser stage."""
    artifact_id: Optional[str] = None
    artifact_type: ArtifactType = ArtifactType.OTHER
    commodity: Commodity = Commodity.OTHER
    supplier_id: Optional[str] = None
    part_number: Optional[str] = None
    entities: ParsedEntities = Field(default_factory=ParsedEntities)
    raw_text: str = ""
    parse_confidence: float = 0.0
    ambiguities: list[str] = Field(default_factory=list)


# ─── RAG Retrieved Context ───────────────────────────────────────────────────

class RetrievedChunk(BaseModel):
    id: str
    source: str  # glossary | eco_corpus | msa
    content: str
    score: float = 0.0
    metadata: dict = Field(default_factory=dict)


class RetrievedContext(BaseModel):
    glossary: list[RetrievedChunk] = Field(default_factory=list)
    eco_precedents: list[RetrievedChunk] = Field(default_factory=list)
    msa_clauses: list[RetrievedChunk] = Field(default_factory=list)


# ─── GSM Brief (Drafting Agent Output) ───────────────────────────────────────

class Translation(BaseModel):
    en: str = ""
    zh: str = ""


class CostImpact(BaseModel):
    trend: CostTrend = CostTrend.NEUTRAL
    unit_price_delta: str = "TBD"
    nre_estimate: str = "TBD"
    reasoning: str = ""
    total_exposure: str = "TBD"


class ScheduleImpact(BaseModel):
    lead_time_delta_weeks: int = 0
    requal_needed: bool = False
    critical_path_risk: str = ""
    milestone_impact: str = ""


class RiskAssessment(BaseModel):
    level: RiskLevel = RiskLevel.LOW
    factors: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    action: str
    owner: str = "GSM"
    confidence: float = 0.0
    requires_approval_from: Optional[str] = None
    citation_refs: list[str] = Field(default_factory=list)


class CitationsUsed(BaseModel):
    glossary: list[str] = Field(default_factory=list)
    eco_precedents: list[str] = Field(default_factory=list)
    msa_clauses: list[str] = Field(default_factory=list)


class GSMBrief(BaseModel):
    """The core output: a structured commercial impact report."""
    translation: Translation = Field(default_factory=Translation)
    cost_impact: CostImpact = Field(default_factory=CostImpact)
    schedule_impact: ScheduleImpact = Field(default_factory=ScheduleImpact)
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    recommended_actions: list[RecommendedAction] = Field(default_factory=list)
    citations_used: CitationsUsed = Field(default_factory=CitationsUsed)
    overall_confidence: float = 0.0
    chain_of_thought: str = ""


class RefusalResponse(BaseModel):
    """Output when the system refuses to generate a brief."""
    is_refusal: bool = True
    reason: str = ""
    missing_info: list[str] = Field(default_factory=list)
    required_clarifications: list[str] = Field(default_factory=list)


# ─── Critic Agent Output ─────────────────────────────────────────────────────

class ReviewIssue(BaseModel):
    type: str  # HALLUCINATION | CITATION_MISSING | LOGIC_ERROR | INCOMPLETE | REFUSAL_ERROR
    severity: str = "WARNING"  # CRITICAL | WARNING | INFO
    location: str = ""
    description: str = ""
    suggested_fix: str = ""


class CitationAudit(BaseModel):
    total_claims: int = 0
    cited_claims: int = 0
    faithfulness_score: float = 0.0


class CriticReview(BaseModel):
    """Output of the Critic Agent."""
    review_passed: bool = False
    issues: list[ReviewIssue] = Field(default_factory=list)
    citation_audit: CitationAudit = Field(default_factory=CitationAudit)
    logic_score: float = 0.0
    recommendation: ReviewRecommendation = ReviewRecommendation.REVISE
    revision_instructions: str = ""


# ─── Pipeline Result ─────────────────────────────────────────────────────────

class PipelineResult(BaseModel):
    """Complete result of the Eng2Biz pipeline."""
    case_id: Optional[str] = None
    input_text: str = ""
    parsed_artifact: ParsedArtifact = Field(default_factory=ParsedArtifact)
    retrieved_context: RetrievedContext = Field(default_factory=RetrievedContext)
    brief: Optional[GSMBrief] = None
    refusal: Optional[RefusalResponse] = None
    critic_review: Optional[CriticReview] = None
    is_published: bool = False
    latency_seconds: float = 0.0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


# ─── Evaluation ──────────────────────────────────────────────────────────────

class DimensionScore(BaseModel):
    score: float = 0.0
    justification: str = ""


class EvalResult(BaseModel):
    """Result from the Model-as-a-Judge."""
    case_id: str
    scores: dict[str, DimensionScore] = Field(default_factory=dict)
    overall_score: float = 0.0
    win_vs_gold: bool = False
    critical_failures: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
