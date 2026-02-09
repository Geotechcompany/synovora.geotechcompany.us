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
        goal="Create informative, educational LinkedIn posts that teach readers with practical hacks and tips, and drive engagement with 6-7 hashtags",
        backstory="""You are an expert LinkedIn content creator who specializes in educational, value-packed posts.
        Your posts teach people something useful: concrete hacks, tips, or insights they can apply.
        You write in a conversational yet professional tone, lead with a hook, and always include 6-7 relevant
        hashtags at the end. You avoid fluff and make every sentence informative.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )


def create_editor_agent(llm):
    """Create the Editor agent for refining posts."""
    return Agent(
        role="Content Editor",
        goal="Refine and polish LinkedIn posts so they are informative, include teachable hacks, and end with 6-7 hashtags",
        backstory="""You are a meticulous editor specializing in LinkedIn content. You ensure posts are:
        - Informative and educational (teach at least one concrete hack or tip)
        - Under 150 words
        - Have a compelling hook in the first two lines
        - Include genuine insights or actionable advice
        - End with an engaging question, then 6-7 relevant hashtags on the next line
        - Use emojis naturally (not overused)
        - Sound personal yet smart
        - Avoid jargon and corporate speak
        - Are ready for professional publication""",
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

            Requirements:
            - Be INFORMATIVE: teach the reader something useful (a hack, tip, or insight they can use).
            - Include at least one concrete, actionable hack or tip (e.g. "Do X to get Y", "3 ways to...", "The one thing that changed...").
            - Keep it under 150 words (excluding hashtags).
            - Start with a hook in the first two lines that grabs attention.
            - Include a genuine insight or thought-provoking point.
            - End with a question that encourages engagement.
            - On the LAST line, add 6 to 7 relevant hashtags (e.g. #Leadership #Productivity #CareerTips). No spaces inside hashtags; separate with spaces.
            - Use emojis naturally (1-3 max, strategically placed).
            - Avoid jargon and corporate speak; sound personal yet smart.
            - If live trend research is provided, incorporate ONE timely detail and keep it current.

            Make it feel authentic and human - like something a real person would post, not AI-generated content."""

            # Create tasks
            creation_task_context = [trend_task] if trend_task else None
            creation_task = Task(
                description=generation_prompt,
                agent=content_creator,
                expected_output="A draft LinkedIn post that teaches a hack or tip, is informative, and ends with 6-7 hashtags",
                context=creation_task_context,
            )
            tasks.append(creation_task)

            editing_task = Task(
                description="""
                Review and refine the LinkedIn post draft. Ensure it:

                1. Is INFORMATIVE and teaches at least one concrete hack or tip.
                2. Is under 150 words (strict limit; hashtags don't count).
                3. Has a compelling hook in the first 1-2 lines.
                4. Contains genuine insights or actionable advice.
                5. Ends with an engaging question, then a final line with exactly 6-7 relevant hashtags (e.g. #Leadership #Productivity).
                6. Uses emojis naturally (1-3 max, not overused).
                7. Avoids jargon and sounds human; is polished and ready for publication.

                If the post is too long, trim it while preserving the key message, hook, and hack/tip.
                If it lacks a clear hack or tip, add one. If it lacks 6-7 hashtags, add them on the last line.
                Ensure the tone is personal yet professional and informative.
                Remove any outdated year references unless explicitly requested.

                Output ONLY the final refined post text, nothing else.
                """,
                agent=editor,
                expected_output="A polished, informative LinkedIn post with a hack/tip and 6-7 hashtags on the last line",
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




