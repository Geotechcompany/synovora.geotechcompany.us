"""CrewAI agent that summarizes scraped LinkedIn profile data."""

import json
import os
from typing import Any, Dict, Optional

from crewai import Agent, Crew, Task
from langchain_openai import ChatOpenAI


def _build_llm(openai_api_key: Optional[str] = None):
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    nvidia_base_url = os.getenv("NVIDIA_BASE_URL")
    nvidia_model = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if gemini_api_key:
        return "gemini/gemini-2.5-flash"

    if nvidia_api_key and nvidia_base_url:
        model_name = nvidia_model if nvidia_model.startswith("openai/") else f"openai/{nvidia_model}"
        return ChatOpenAI(
            model=model_name,
            base_url=nvidia_base_url,
            api_key=nvidia_api_key,
            temperature=0.2,
            max_tokens=600,
        )

    if openai_api_key or os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(
            model=openai_model,
            api_key=openai_api_key,
            temperature=0.2,
            max_tokens=600,
        )

    raise ValueError(
        "No AI provider configured. Set GEMINI_API_KEY or (NVIDIA_API_KEY and NVIDIA_BASE_URL), "
        "or store an OpenAI API key for the user (or set OPENAI_API_KEY)."
    )


def analyze_profile_insights(
    scraped_profile: Dict[str, Any],
    metrics: Dict[str, Any],
    content_stats: Dict[str, Any],
) -> str:
    """
    Use CrewAI agent to summarize scraped LinkedIn data for UI display.

    Args:
        scraped_profile: Dict returned from scraper (userProfile, experiences, skills, etc.)
        metrics: Dict with followers/connections counts.
        content_stats: Workspace stats (draft/published counts, avg word count).
    """
    llm = _build_llm()

    analyst = Agent(
        role="LinkedIn Intelligence Analyst",
        goal="Summarize LinkedIn profile intelligence for the dashboard.",
        backstory="""You specialize in personal branding analytics. Given structured profile data,
        you extract tone, expertise, audience signals, and opportunities to tailor AI-generated posts.""",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description=f"""
        Analyze the following data and provide a concise profile insight card suitable for the dashboard:

        Scraped profile JSON: {json.dumps(scraped_profile)[:4000]}

        Metrics: {metrics}

        Workspace content stats: {content_stats}

        Output requirements:
        - 2-3 sentences summarizing persona, voice, and audience proof points.
        - Highlight follower + connection counts (if available) and notable skills/roles.
        - Include one bullet list (max 3 bullets) suggesting content angles based on experiences and skills.
        - Keep tone professional and data-backed.
        """,
        agent=analyst,
        expected_output="Markdown text with summary paragraph plus short bullet list.",
    )

    crew = Crew(agents=[analyst], tasks=[task], verbose=False)
    result = crew.kickoff()
    return str(result).strip()



