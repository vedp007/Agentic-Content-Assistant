from app.models.schemas import ExtractedContent, IntentResult, PlanStep


def build_plan(
    intent: IntentResult,
    extracted: ExtractedContent,
    cost_estimate: dict | None = None,
) -> list[PlanStep]:
    steps: list[PlanStep] = []
    if extracted.source_type != "text":
        steps.append(
            PlanStep(
                name="extract_content",
                status="completed",
                detail=f"Processed {extracted.source_type} input and captured text/metadata.",
            )
        )
    else:
        steps.append(PlanStep(name="read_text", status="completed", detail="Read direct text input."))

    steps.append(
        PlanStep(
            name="detect_intent",
            status="completed",
            detail=f"Detected intent `{intent.intent}` with confidence {intent.confidence:.2f}.",
        )
    )
    if cost_estimate:
        steps.append(
            PlanStep(
                name="estimate_cost",
                status="completed",
                detail=(
                    "Estimated "
                    f"{cost_estimate['total_tokens_estimate']} tokens and "
                    f"${cost_estimate['estimated_cost_usd']:.2f} API cost."
                ),
            )
        )

    if intent.needs_clarification:
        steps.append(
            PlanStep(
                name="ask_follow_up",
                status="completed",
                detail="Stopped before execution because the user goal is ambiguous.",
            )
        )
        return steps

    steps.append(
        PlanStep(
            name="execute_tool",
            status="completed",
            detail=f"Selected the minimal tool for `{intent.intent}`.",
        )
    )
    steps.append(
        PlanStep(name="format_response", status="completed", detail="Returned text-only output.")
    )
    return steps
