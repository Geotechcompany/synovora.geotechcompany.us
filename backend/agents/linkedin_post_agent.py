"""CrewAI agent for generating high-quality LinkedIn posts."""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from crewai import Agent, Crew, Task
from langchain_openai import ChatOpenAI

from utils.trend_fetcher import format_trend_brief


def create_content_creator_agent(llm):
    """Create the Content Creator agent for LinkedIn posts."""
    return Agent(
        role="LinkedIn Content Creator",
        goal="Create clean, human-written, educational LinkedIn posts that teach a clear system or method (like Plan→Setup→Build), explain why it matters, and end with a strong takeaway (no hashtags, no markdown formatting).",
        backstory="""You are an expert LinkedIn content creator who specializes in educational, framework-style posts.
        Your posts teach like a mini-lesson: a clear structure (e.g. 3 phases, key steps, or a simple framework),
        explain the 'why' not just the 'how', and end with one memorable big idea or takeaway.
        You use numbered points or short bullets when it helps. You avoid fluff; every line adds value.
        You write in a conversational yet professional tone, lead with a hook, and teach a repeatable approach
        (a system), not just one random tip.

        Formatting rules:
        - Output MUST be plain text only (no markdown).
        - Do NOT use asterisks, bold, headings, or hashtag lines.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )


def create_editor_agent(llm):
    """Create the Editor agent for refining posts."""
    return Agent(
        role="Content Editor",
        goal="Refine posts so they are clearly educational: a framework or structure, a clear why, and one big takeaway (plain text only; no hashtags, no markdown).",
        backstory="""You are a meticulous editor specializing in educational LinkedIn content. You ensure posts:
        - Teach a clear framework, system, or method (e.g. 3 steps, phases, or key principles)—not just one isolated tip
        - Explain why it matters (context, common mistakes, or the shift in thinking)
        - Include a memorable big idea or takeaway (one line the reader can keep)
        - Are under 150 words, with a strong hook (no hashtag line)
        - Use structure (numbered points or short bullets) when it helps clarity
        - Sound personal yet smart; avoid jargon; are ready for publication""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )


def create_trend_research_agent(llm):
    """Create the research agent responsible for trend scouting."""
    return Agent(
        role="Trend Research Analyst",
        goal="Continuously surface timely, buzzworthy angles tailored to the user's niche",
        backstory="""You're a cultural strategist who combines live web research with instincts for what
        performs on LinkedIn. You distill breaking stories, stats, and hype into snackable angles others
        can immediately riff on.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def _compress_profile_context(profile_context: Optional[Dict[str, Optional[str]]]) -> str:
    """Turn LinkedIn profile details into a short narrative for prompting."""
    if not profile_context:
        return ""

    pieces = []
    headline = profile_context.get("headline")
    bio = profile_context.get("bio")
    industry = profile_context.get("industry")

    if headline:
        pieces.append(f"Headline: {headline}")
    if industry:
        pieces.append(f"Industry: {industry}")
    if bio:
        pieces.append(f"About/Bio: {bio}")

    return "\n".join(pieces)


def generate_linkedin_post(
    topic: str,
    additional_context: Optional[str] = None,
    profile_context: Optional[Dict[str, Optional[str]]] = None,
    trending_topics: Optional[List[Dict[str, Optional[str]]]] = None,
    user_niche: Optional[str] = None,
    openai_api_key: Optional[str] = None,
) -> str:
    """
    Generate a LinkedIn post using CrewAI agents.
    
    Args:
        topic: The main topic for the post
        additional_context: Optional additional context or requirements
        
    Returns:
        Generated LinkedIn post content
    """
    now = datetime.now(timezone.utc)
    today_iso = now.date().isoformat()
    current_year = now.year

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
                    temperature=0.7,
                    max_tokens=500,
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
                    temperature=0.7,
                    max_tokens=500,
                ),
            )
        )

    if not providers:
        raise ValueError(
            "No AI provider configured. Set GEMINI_API_KEY or (NVIDIA_API_KEY and NVIDIA_BASE_URL), "
            "or store an OpenAI API key for the user (or set OPENAI_API_KEY)."
        )
    
    last_error: Optional[Exception] = None
    for provider_name, llm in providers:
        try:
            # Create agents (conditionally include research analyst)
            agents = []
            tasks = []

            trend_task = None
            if trending_topics:
                trend_agent = create_trend_research_agent(llm)
                agents.append(trend_agent)

                trend_brief = format_trend_brief(trending_topics)
                research_prompt = f"""
                You are scouting timely topics for a LinkedIn creator.
                Today's date (UTC): {today_iso}. The current year is {current_year}.

                User niche: {user_niche or 'General professional audience'}
                Requested angle/topic: {topic}

                Live internet research results:
                {trend_brief}

                Requirements:
                - Output 3 concise conversation starters tailored to the user niche
                - Each starter must reference one of the live findings or data points
                - Include one punchy supporting insight or stat per starter
                - Focus on themes that can lead to fun, witty, and high-signal posts
                - Keep bullets under 40 words
                - Do NOT mention outdated years (e.g. 2025) unless a live finding explicitly references it.

                Respond ONLY with the three bullet points.
                """.strip()

                trend_task = Task(
                    description=research_prompt,
                    agent=trend_agent,
                    expected_output="Three bullet points highlighting trend-backed conversational angles.",
                )
                tasks.append(trend_task)

            content_creator = create_content_creator_agent(llm)
            editor = create_editor_agent(llm)
            agents.extend([content_creator, editor])

            # Build the generation prompt
            profile_summary = _compress_profile_context(profile_context)
            generation_prompt = f"""Write a high-IQ, human-style LinkedIn post about {topic}.

            Date context:
            - Today's date (UTC): {today_iso}
            - Current year: {current_year}
            - Do NOT say "as we approach 2025" or reference outdated years unless the user asked for it.
            """.strip()

            if additional_context:
                generation_prompt += f"\n\nAdditional context: {additional_context}"

            if profile_summary:
                generation_prompt += f"\n\nAuthor context:\n{profile_summary}"
            elif user_niche:
                generation_prompt += f"\n\nAuthor niche: {user_niche}"

            generation_prompt += """

            Requirements (educational, framework-style—like a mini-lesson):
            - Output MUST be plain text only (no markdown). Do NOT use asterisks, bold, headings, or hashtag lines.
            - Teach a clear FRAMEWORK or SYSTEM (e.g. "3 phases", "Plan → Do → Review", key steps or principles). Not just one random tip—a repeatable approach.
            - Explain the WHY: why this matters, common mistakes, or the shift in thinking (e.g. "Stop X. Start Y.").
            - Include one memorable BIG IDEA or takeaway (one line the reader can remember and apply).
            - Use structure when it helps: short numbered points or short bullets (but keep it clean and readable).
            - Keep it under 150 words. Start with a hook; end with an engaging question.
            - No hashtags.
            - Use emojis naturally (0-2 max). Avoid jargon; sound personal yet smart.
            - If live trend research is provided, incorporate ONE timely detail and keep it current.

            Make it feel like an expert sharing a framework—clear intent, structure, and one takeaway—not generic AI fluff."""

            # Create tasks
            creation_task_context = [trend_task] if trend_task else None
            creation_task = Task(
                description=generation_prompt,
                agent=content_creator,
                expected_output="A clean, plain-text educational post with a clear framework (phases/steps), a why, and one big takeaway (no hashtags, no markdown).",
                context=creation_task_context,
            )
            tasks.append(creation_task)

            editing_task = Task(
                description="""
                Review and refine the LinkedIn post draft. Ensure it:

                1. Is plain text only (NO markdown). Do NOT use asterisks, bold, headings, or hashtag lines.
                2. Teaches a clear FRAMEWORK or SYSTEM (phases, steps, or key principles)—not just one isolated tip. Has a memorable big idea or takeaway.
                3. Explains the WHY (why it matters, common mistakes, or shift in thinking).
                4. Is under 150 words (strict limit). Has a compelling hook in the first 1-2 lines.
                5. Uses structure (numbered points or short bullets) where it helps.
                6. Ends with an engaging question.
                7. Has NO hashtags.
                8. Uses emojis naturally (0-2 max). Avoids jargon; sounds human and ready for publication.

                If the post is too long, trim while keeping the framework, hook, and big takeaway.
                If it lacks a clear framework or takeaway, add one. If it contains hashtags or markdown symbols, remove them.
                Remove any outdated year references unless explicitly requested.

                Output ONLY the final refined post text, nothing else.
                """,
                agent=editor,
                expected_output="A polished, educational LinkedIn post in clean plain text (no hashtags, no markdown).",
                context=[creation_task],
            )
            tasks.append(editing_task)

            print(f"Using AI provider: {provider_name}")
            crew = Crew(
                agents=agents,
                tasks=tasks,
                verbose=True,
            )

            result = crew.kickoff()
            post_text = str(result).strip()
            if post_text.startswith('"') and post_text.endswith('"'):
                post_text = post_text[1:-1]
            return post_text
        except Exception as exc:
            last_error = exc
            continue

    raise ValueError(f"All AI providers failed. Last error: {last_error}")


if __name__ == "__main__":
    # Test the agent
    test_topic = "The future of remote work and its impact on team collaboration"
    print("Generating LinkedIn post...")
    print("\n" + "="*50)
    post = generate_linkedin_post(test_topic)
    print("\nGenerated Post:")
    print("-"*50)
    print(post)
    print("-"*50)
    print(f"\nWord count: {len(post.split())} words")




