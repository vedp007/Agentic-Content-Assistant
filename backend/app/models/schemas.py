from typing import Any, Literal

from pydantic import BaseModel, Field


class ExtractedContent(BaseModel):
    source_type: Literal["text", "image", "pdf", "audio", "youtube", "unknown"]
    text: str = ""
    confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class IntentResult(BaseModel):
    intent: str
    confidence: float
    needs_clarification: bool = False
    follow_up_question: str | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class PlanStep(BaseModel):
    name: str
    status: Literal["pending", "completed", "skipped"] = "pending"
    detail: str


class AgentResponse(BaseModel):
    response: str
    extracted_text: str = ""
    intent: IntentResult
    plan: list[PlanStep]
    logs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

