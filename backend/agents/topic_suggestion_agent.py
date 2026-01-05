"""AI agent for suggesting LinkedIn post topics based on a user's occupation + live trends."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from crewai import Agent, Crew, Task
from langchain_openai import ChatOpenAI

from utils.trend_fetcher import format_trend_brief


def suggest_topics(
    *,
    occupation: str,
    trending_topics: Optional[List[Dict[str, Optional[str]]]] = None,
    limit: int = 8,
    openai_api_key: Optional[str] = None,
) -> List[str]:
    now = datetime.now(timezone.utc)
    today_iso = now.date().isoformat()
    current_year = now.year

    occupation_clean = (occupation or "").strip()
    if not occupation_clean:
        raise ValueError("occupation is required")

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    nvidia_base_url = os.getenv("NVIDIA_BASE_URL")
    nvidia_model = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    providers: List[tuple[str, object]] = []
    if gemini_api_key:
        providers.append(("gemini", "gemini/gemini-2.5-flash"))
    if nvidia_api_key and nvidia_base_url:
        model_name = nvidia_model if nvidia_model.startswith("openai/") else f"openai/{nvidia_model}"
        providers.append(
            (
                "nvidia",
                ChatOpenAI(
                    model=model_name,
                    base_url=nvidia_base_url,
                    api_key=nvidia_api_key,
                    temperature=0.5,
                    max_tokens=400,
                ),
            )
        )
    if openai_api_key or os.getenv("OPENAI_API_KEY"):
        providers.append(
            (
                "openai",
                ChatOpenAI(
                    model=openai_model,
                    api_key=openai_api_key,
                    temperature=0.5,
                    max_tokens=400,
                ),
            )
        )

    if not providers:
        raise ValueError(
            "No AI provider configured. Set GEMINI_API_KEY or (NVIDIA_API_KEY and NVIDIA_BASE_URL), "
            "or store an OpenAI API key for the user (or set OPENAI_API_KEY)."
        )

    limit = max(3, min(int(limit or 8), 20))
    trend_brief = format_trend_brief(trending_topics) if trending_topics else "No live trend data was available."

    last_error: Optional[Exception] = None
    for provider_name, llm in providers:
        try:
            agent = Agent(
                role="Topic Strategist",
                goal="Generate timely, high-signal LinkedIn post topic ideas tailored to the user's occupation.",
                backstory="You are a senior LinkedIn growth strategist who turns fresh industry signals into strong post angles.",
                llm=llm,
                verbose=False,
                allow_delegation=False,
            )

            prompt = f"""
            Generate {limit} LinkedIn post topic ideas for this occupation:
            Occupation: {occupation_clean}

            Date context:
            - Today's date (UTC): {today_iso}
            - Current year: {current_year}
            - Never say "as we approach 2025" or reference outdated years unless a live trend explicitly references it.

            Live trend research (may be empty):
            {trend_brief}

            Requirements:
            - Output EXACTLY {limit} items.
            - Each item should be a short title (5-12 words), not a full post.
            - Make them specific and actionable (not generic).
            - If live trend research is provided, incorporate at least ONE timely detail across the list.
            - Keep them suitable for LinkedIn professionals in this occupation.
            - Respond ONLY as a JSON array of strings (no markdown, no extra text).
            """.strip()

            task = Task(
                description=prompt,
                agent=agent,
                expected_output="JSON array of strings.",
            )

            crew = Crew(agents=[agent], tasks=[task], verbose=False)
            result = str(crew.kickoff()).strip()

            # Parse JSON array of strings.
            import json as _json

            parsed = _json.loads(result)
            if not isinstance(parsed, list):
                raise ValueError("AI did not return a JSON array.")
            topics: List[str] = []
            for item in parsed:
                if isinstance(item, str):
                    cleaned = item.strip().strip('"').strip()
                    if cleaned:
                        topics.append(cleaned)
            if len(topics) < 3:
                raise ValueError("AI returned too few topic suggestions.")
            return topics[:limit]
        except Exception as exc:
            last_error = exc
            continue

    raise ValueError(f"All AI providers failed to suggest topics. Last error: {last_error}")


