"""Utility for fetching trending topics from the public web (Serper.dev).

Combines:
- Google search & news: general profession/industry trending topics (not LinkedIn-specific).
- Reddit: latest discussions and trends on the profession via site:reddit.com search.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import requests


def _normalize_item(
    item: dict,
    source_label: str,
) -> Optional[Dict[str, Optional[str]]]:
    title = (item.get("title") or item.get("snippet") or "").strip()
    if not title:
        return None
    snippet = (item.get("snippet") or item.get("summary") or item.get("content") or "").strip()
    link = item.get("link") or item.get("url")
    return {
        "title": title,
        "snippet": snippet,
        "source": source_label or item.get("source") or link,
        "link": link,
        "date": item.get("date"),
    }


class TrendingTopicFetcher:
    """Fetches trends from Google/news (general profession) and Reddit via Serper.dev."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_results: int = 5,
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.search_base = (
            base_url or os.getenv("SERPER_BASE_URL") or "https://google.serper.dev/search"
        ).rstrip("/")
        if self.search_base.endswith("/search"):
            self.search_base = self.search_base[: -len("/search")]
        self.search_base = self.search_base or "https://google.serper.dev"
        self.max_results = max(1, max_results)
        self.timeout = timeout

    def is_configured(self) -> bool:
        """Return True when an API key is available."""
        return bool(self.api_key)

    def _serper_post(self, q: str, country: str = "us", language: str = "en", num: int = 10) -> dict:
        """Run a single Serper search. Returns parsed JSON."""
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "q": q,
            "gl": country.lower(),
            "hl": language.lower(),
            "num": num,
        }
        url = f"{self.search_base}/search"
        response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _fetch_google_trends(
        self,
        niche: str,
        topic_hint: Optional[str],
        country: str,
        language: str,
    ) -> List[Dict[str, Optional[str]]]:
        """Google/search: general profession trending topics and industry news (not LinkedIn-specific)."""
        parts = [p for p in [topic_hint.strip() if topic_hint else None, niche.strip() if niche else None] if p]
        parts.extend(["trending topics", "industry news"])
        query = " ".join(parts)
        if not query:
            return []
        try:
            data = self._serper_post(query, country=country, language=language, num=10)
        except Exception:
            return []
        candidates = data.get("news") or data.get("organic") or []
        out: List[Dict[str, Optional[str]]] = []
        for item in candidates:
            norm = _normalize_item(item, "Google")
            if norm:
                out.append(norm)
        return out

    def _fetch_reddit_trends(
        self,
        niche: str,
        topic_hint: Optional[str],
        country: str,
        language: str,
    ) -> List[Dict[str, Optional[str]]]:
        """Reddit: latest discussions and trends on the profession (site:reddit.com)."""
        parts = [p for p in [niche.strip() if niche else None, topic_hint.strip() if topic_hint else None] if p]
        if not parts:
            return []
        query = "site:reddit.com " + " ".join(parts) + " trending discussions hot"
        try:
            data = self._serper_post(query, country=country, language=language, num=10)
        except Exception:
            return []
        candidates = data.get("organic") or []
        out: List[Dict[str, Optional[str]]] = []
        for item in candidates:
            norm = _normalize_item(item, "Reddit")
            if norm and "reddit.com" in (norm.get("link") or ""):
                out.append(norm)
        return out

    def fetch_topics(
        self,
        niche: str,
        topic_hint: Optional[str] = None,
        country: str = "us",
        language: str = "en",
    ) -> List[Dict[str, Optional[str]]]:
        """
        Fetch trending topics for the profession from Google/news and Reddit.

        - Google: general profession trending topics and industry news (not LinkedIn-specific).
        - Reddit: latest discussions and hot topics on the profession.

        Args:
            niche: User profession/niche (e.g. Software Engineering, Marketing).
            topic_hint: Optional extra topic or campaign goal.
            country: ISO country code for geo-targeting (default: US).
            language: Content language (default: English).

        Returns:
            List of trend items (title, snippet, source, link, date); mixed from Google and Reddit.
        """
        if not self.api_key:
            raise ValueError("SERPER_API_KEY is not configured")

        niche = (niche or "").strip()
        topic_hint = (topic_hint or "").strip() or None
        if not niche:
            raise ValueError("niche (profession) is required to build the trend query")

        seen_links: set = set()
        combined: List[Dict[str, Optional[str]]] = []

        # 1) Google / news: general profession trends
        for t in self._fetch_google_trends(niche, topic_hint, country, language):
            link = (t.get("link") or "").strip()
            key = link or (t.get("title") or "")
            if key and key not in seen_links:
                seen_links.add(key)
                combined.append(t)
            if len(combined) >= self.max_results:
                return combined

        # 2) Reddit: profession discussions and trends
        for t in self._fetch_reddit_trends(niche, topic_hint, country, language):
            link = (t.get("link") or "").strip()
            key = link or (t.get("title") or "")
            if key and key not in seen_links:
                seen_links.add(key)
                combined.append(t)
            if len(combined) >= self.max_results:
                return combined

        return combined[: self.max_results]


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


