"""Centralized pricing logic for LLM models"""

from typing import Any, Dict

# Model pricing in USD per 1000 tokens
# Based on public pricing as of 2024
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # OpenAI GPT models
    "gpt-5": {
        "prompt_per_1k": 0.015,
        "completion_per_1k": 0.045,
    },
    "gpt-4-turbo": {
        "prompt_per_1k": 0.01,
        "completion_per_1k": 0.03,
    },
    "gpt-4": {
        "prompt_per_1k": 0.03,
        "completion_per_1k": 0.06,
    },
    "gpt-3.5-turbo": {
        "prompt_per_1k": 0.0015,
        "completion_per_1k": 0.002,
    },
    # Anthropic Claude models
    "claude-sonnet-4-20250514": {
        "prompt_per_1k": 0.003,
        "completion_per_1k": 0.015,
    },
    "claude-3-sonnet-20240229": {
        "prompt_per_1k": 0.003,
        "completion_per_1k": 0.015,
    },
    "claude-3-opus-20240229": {
        "prompt_per_1k": 0.015,
        "completion_per_1k": 0.075,
    },
    "claude-3-haiku-20240307": {
        "prompt_per_1k": 0.00025,
        "completion_per_1k": 0.00125,
    },
    # Google Gemini models
    "gemini-2.5-pro": {
        "prompt_per_1k": 0.00035,
        "completion_per_1k": 0.0014,
    },
    "gemini-1.5-pro": {
        "prompt_per_1k": 0.00035,
        "completion_per_1k": 0.0014,
    },
    "gemini-1.5-flash": {
        "prompt_per_1k": 0.000075,
        "completion_per_1k": 0.0003,
    },
}

# Default pricing for unknown models (conservative estimate)
DEFAULT_PRICING = {
    "prompt_per_1k": 0.01,
    "completion_per_1k": 0.03,
}


def get_model_pricing(model: str) -> Dict[str, Any]:
    """Get pricing for a specific model"""
    # Handle model aliases and variations
    model_lower = model.lower()

    # Direct match
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    # Partial match (e.g., "gpt-4-0125-preview" -> "gpt-4")
    for known_model, pricing in MODEL_PRICING.items():
        if known_model in model_lower:
            return pricing

    # Return default pricing for unknown models
    return DEFAULT_PRICING


def calculate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate cost in USD for given token counts"""
    pricing = get_model_pricing(model)

    prompt_cost = (prompt_tokens / 1000) * pricing["prompt_per_1k"]
    completion_cost = (completion_tokens / 1000) * pricing["completion_per_1k"]

    return float(round(prompt_cost + completion_cost, 6))


def estimate_book_cost(
    model: str,
    target_chapters: int = 12,
    avg_prompt_tokens_per_chapter: int = 2000,
    avg_completion_tokens_per_chapter: int = 4000,
    include_outline: bool = True,
    include_editing: bool = True,
    include_continuity: bool = True,
) -> Dict[str, Any]:
    """Estimate total cost for generating a book"""
    # Base chapter generation
    chapter_prompt_tokens = target_chapters * avg_prompt_tokens_per_chapter
    chapter_completion_tokens = target_chapters * avg_completion_tokens_per_chapter

    # Outline generation (roughly 1 chapter worth)
    outline_prompt_tokens = avg_prompt_tokens_per_chapter if include_outline else 0
    outline_completion_tokens = avg_completion_tokens_per_chapter if include_outline else 0

    # Editing pass (60% of original generation)
    edit_prompt_tokens = int(chapter_prompt_tokens * 0.6) if include_editing else 0
    edit_completion_tokens = int(chapter_completion_tokens * 0.6) if include_editing else 0

    # Continuity checking (20% of original)
    continuity_prompt_tokens = int(chapter_prompt_tokens * 0.2) if include_continuity else 0
    continuity_completion_tokens = int(chapter_completion_tokens * 0.2) if include_continuity else 0

    # Total tokens
    total_prompt_tokens = (
        chapter_prompt_tokens
        + outline_prompt_tokens
        + edit_prompt_tokens
        + continuity_prompt_tokens
    )
    total_completion_tokens = (
        chapter_completion_tokens
        + outline_completion_tokens
        + edit_completion_tokens
        + continuity_completion_tokens
    )

    # Calculate costs
    total_cost = calculate_cost_usd(model, total_prompt_tokens, total_completion_tokens)

    return {
        "estimated_usd": total_cost,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "breakdown": {
            "chapters": calculate_cost_usd(model, chapter_prompt_tokens, chapter_completion_tokens),
            "outline": calculate_cost_usd(model, outline_prompt_tokens, outline_completion_tokens),
            "editing": calculate_cost_usd(model, edit_prompt_tokens, edit_completion_tokens),
            "continuity": calculate_cost_usd(
                model, continuity_prompt_tokens, continuity_completion_tokens
            ),
        },
        "model": model,
        "chapters": target_chapters,
    }
