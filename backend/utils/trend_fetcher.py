"""Utility for fetching trending topics from the public web (Serper.dev)."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import requests


class TrendingTopicFetcher:
    """Simple wrapper around Serper.dev (Google SERP API) for trend discovery."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_results: int = 5,
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = (
            base_url or os.getenv("SERPER_BASE_URL") or "https://google.serper.dev/search"
        )
        self.max_results = max(1, max_results)
        self.timeout = timeout

    def is_configured(self) -> bool:
        """Return True when an API key is available."""
        return bool(self.api_key)

    def fetch_topics(
        self,
        niche: str,
        topic_hint: Optional[str] = None,
        country: str = "us",
        language: str = "en",
    ) -> List[Dict[str, Optional[str]]]:
        """
        Fetch trending news/topics for the supplied niche.

        Args:
            niche: User niche or specialization used to shape the query.
            topic_hint: Optional topic or campaign goal provided by the user.
            country: ISO country code for geo-targeting (default: US).
            language: Content language (default: English).

        Returns:
            List of dictionaries describing trending items.
        """
        if not self.api_key:
            raise ValueError("SERPER_API_KEY is not configured")

        query_parts = [
            topic_hint.strip() if topic_hint else None,
            niche.strip() if niche else None,
            "LinkedIn conversation trend",
            "emerging insights",
        ]
        query = " ".join([part for part in query_parts if part])
        if not query:
            raise ValueError("A query could not be built for the trend request")

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": query,
            "gl": country.lower(),
            "hl": language.lower(),
            "num": min(10, self.max_results * 2),
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        candidates = data.get("news") or data.get("organic") or []
        trends: List[Dict[str, Optional[str]]] = []
        for item in candidates:
            title = (item.get("title") or item.get("snippet") or "").strip()
            if not title:
                continue

            snippet = (item.get("snippet") or item.get("summary") or "").strip()
            trends.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "source": item.get("source") or item.get("link"),
                    "link": item.get("link"),
                    "date": item.get("date"),
                }
            )

            if len(trends) >= self.max_results:
                break

        return trends


def format_trend_brief(
    trends: Optional[List[Dict[str, Optional[str]]]], max_items: int = 5
) -> str:
    """Turn raw trend data into a compact human-readable bullet list."""
    if not trends:
        return "No live trend data was available."

    lines = []
    for idx, trend in enumerate(trends[:max_items], start=1):
        snippet = trend.get("snippet") or ""
        source = trend.get("source") or trend.get("date") or "web"
        line = f"{idx}. {trend.get('title')} — {snippet} (source: {source})"
        lines.append(line.strip())

    return "\n".join(lines)

__all__ = ["TrendingTopicFetcher", "format_trend_brief"]


