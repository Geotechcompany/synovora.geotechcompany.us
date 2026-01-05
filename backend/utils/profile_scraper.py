"""Headless LinkedIn scraping utilities implemented in Python with Playwright."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, Tuple

from dateutil import parser as date_parser
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright


def is_scraper_configured() -> bool:
    """Return True when required env vars exist."""
    return bool(os.getenv("LINKEDIN_SCRAPER_LI_AT"))


def clean_text(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    cleaned = re.sub(r"(\r\n|\r|\n)", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.replace("See more", "").replace("See less", "").strip()
    return cleaned or None


def parse_count_text(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    digits = re.findall(r"\d+", value.replace(",", ""))
    if not digits:
        return None
    try:
        return int("".join(digits))
    except ValueError:
        return None


def format_date(value: Optional[str]) -> Optional[str]:
    if not value or value.lower() == "present":
        return None if value is None else "Present"
    try:
        return date_parser.parse(value).isoformat()
    except (ValueError, OverflowError):
        return value


def get_duration_in_days(start: Optional[str], end: Optional[str]) -> Optional[int]:
    if not start or not end or end == "Present":
        return None
    try:
        start_dt = date_parser.parse(start)
        end_dt = date_parser.parse(end)
        return (end_dt - start_dt).days + 1
    except (ValueError, OverflowError):
        return None


def _auto_scroll(page) -> None:
    page.evaluate(
        """() => new Promise((resolve) => {
        let totalHeight = 0;
        const distance = 500;
        const timer = setInterval(() => {
            const scrollHeight = document.body.scrollHeight;
            window.scrollBy(0, distance);
            totalHeight += distance;
            if (totalHeight >= scrollHeight) {
                clearInterval(timer);
                resolve();
            }
        }, 100);
    })"""
    )


def _click_buttons(page, selectors) -> None:
    for selector in selectors:
        try:
            handle = page.query_selector(selector)
            if handle:
                handle.click()
        except Exception:
            continue


def scrape_linkedin_profile(profile_url: Optional[str] = None, timeout: int = 90) -> Dict[str, Any]:
    """
    Scrape a public LinkedIn profile using Playwright and return structured data.

    Args:
        profile_url: The LinkedIn profile URL to scrape. If omitted, uses LINKEDIN_SCRAPER_PROFILE_URL.
        timeout: Max seconds for network/navigation operations.
    """
    li_at = os.getenv("LINKEDIN_SCRAPER_LI_AT")
    if not li_at:
        raise ValueError("LINKEDIN_SCRAPER_LI_AT must be set with the LinkedIn li_at cookie value.")

    target_url = profile_url or os.getenv("LINKEDIN_SCRAPER_PROFILE_URL")
    if not target_url:
        raise ValueError("LinkedIn profile URL not provided. Set LINKEDIN_SCRAPER_PROFILE_URL or pass profile_url.")

    timeout_ms = int(timeout * 1000)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1366,768",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=os.getenv(
                "LINKEDIN_SCRAPER_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
            ),
        )

        context.add_cookies(
            [
                {
                    "name": "li_at",
                    "value": li_at,
                    "domain": ".www.linkedin.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                }
            ]
        )

        page = context.new_page()

        try:
            page.goto("https://www.linkedin.com/feed/", wait_until="networkidle", timeout=timeout_ms)
            if page.url.endswith("/login"):
                raise RuntimeError("LinkedIn session cookie expired. Please refresh LINKEDIN_SCRAPER_LI_AT.")

            page.goto(target_url, wait_until="networkidle", timeout=timeout_ms)
            _auto_scroll(page)
            _click_buttons(
                page,
                [
                    ".pv-profile-section.pv-about-section .lt-line-clamp__more",
                    "#experience-section .pv-profile-section__see-more-inline.link",
                    ".pv-profile-section.education-section button.pv-profile-section__see-more-inline",
                    ".pv-skill-categories-section [data-control-name='skill_details']",
                ],
            )

            page.wait_for_timeout(500)

            raw_profile = page.evaluate(
                """() => {
                const profileSection = document.querySelector('.pv-top-card');
                const bulletItems = Array.from(profileSection?.querySelectorAll('.pv-top-card--list-bullet li') || []);

                const connectionsCountText = (bulletItems.find(el => el.textContent?.toLowerCase().includes('connection'))?.textContent || null);
                const followersCountText = (bulletItems.find(el => el.textContent?.toLowerCase().includes('follower'))?.textContent || null);

                const description = document.querySelector('.pv-about__summary-text .lt-line-clamp__raw-line');

                return {
                    fullName: profileSection?.querySelector('.pv-top-card--list li:first-child')?.textContent || null,
                    title: profileSection?.querySelector('h2')?.textContent || null,
                    location: profileSection?.querySelector('.pv-top-card--list.pv-top-card--list-bullet.mt1 li:first-child')?.textContent || null,
                    photo: (profileSection?.querySelector('.pv-top-card__photo') || profileSection?.querySelector('.profile-photo-edit__preview'))?.getAttribute('src') || null,
                    description: description?.textContent || null,
                    url: window.location.href,
                    connectionsCountText,
                    followersCountText
                };
            }"""
            )

            raw_experiences = page.eval_on_selector_all(
                "#experience-section ul > .ember-view",
                """nodes => nodes.map(node => {
                    const titleElement = node.querySelector('h3');
                    const employmentTypeElement = node.querySelector('span.pv-entity__secondary-title');
                    const companyElement = node.querySelector('.pv-entity__secondary-title');
                    const descriptionElement = node.querySelector('.pv-entity__description');
                    const dateRangeElement = node.querySelector('.pv-entity__date-range span:nth-child(2)');
                    const locationElement = node.querySelector('.pv-entity__location span:nth-child(2)');

                    const dateRangeText = dateRangeElement?.textContent || null;
                    const startDatePart = dateRangeText?.split('–')[0] || null;
                    const endDatePart = dateRangeText?.split('–')[1] || null;
                    const endDateIsPresent = endDatePart?.trim().toLowerCase() === 'present' || false;
                    const endDate = (endDatePart && !endDateIsPresent) ? endDatePart.trim() : 'Present';

                    return {
                        title: titleElement?.textContent || null,
                        employmentType: employmentTypeElement?.textContent || null,
                        company: companyElement?.textContent || null,
                        location: locationElement?.textContent || null,
                        description: descriptionElement?.textContent || null,
                        startDate: startDatePart?.trim() || null,
                        endDate,
                        endDateIsPresent
                    };
                })""",
            )

            raw_education = page.eval_on_selector_all(
                "#education-section ul > .ember-view",
                """nodes => nodes.map(node => {
                    const schoolNameElement = node.querySelector('h3.pv-entity__school-name');
                    const degreeNameElement = node.querySelector('.pv-entity__degree-name .pv-entity__comma-item');
                    const fieldOfStudyElement = node.querySelector('.pv-entity__fos .pv-entity__comma-item');
                    const dateRangeElement = node.querySelectorAll('.pv-entity__dates time');

                    return {
                        schoolName: schoolNameElement?.textContent || null,
                        degreeName: degreeNameElement?.textContent || null,
                        fieldOfStudy: fieldOfStudyElement?.textContent || null,
                        startDate: dateRangeElement[0]?.textContent || null,
                        endDate: dateRangeElement[1]?.textContent || null
                    };
                })""",
            )

            raw_volunteer = page.eval_on_selector_all(
                ".pv-profile-section.volunteering-section ul > li.ember-view",
                """nodes => nodes.map(node => {
                    const titleElement = node.querySelector('.pv-entity__summary-info h3');
                    const companyElement = node.querySelector('.pv-entity__summary-info span.pv-entity__secondary-title');
                    const dateRangeElement = node.querySelector('.pv-entity__date-range span:nth-child(2)');
                    const descriptionElement = node.querySelector('.pv-entity__description');

                    const dateRangeText = dateRangeElement?.textContent || null;
                    const startDatePart = dateRangeText?.split('–')[0] || null;
                    const endDatePart = dateRangeText?.split('–')[1] || null;
                    const endDateIsPresent = endDatePart?.trim().toLowerCase() === 'present' || false;
                    const endDate = (endDatePart && !endDateIsPresent) ? endDatePart.trim() : 'Present';

                    return {
                        title: titleElement?.textContent || null,
                        company: companyElement?.textContent || null,
                        description: descriptionElement?.textContent || null,
                        startDate: startDatePart?.trim() || null,
                        endDate,
                        endDateIsPresent
                    };
                })""",
            )

            raw_skills = page.eval_on_selector_all(
                ".pv-skill-categories-section [data-control-name='skill_details']",
                """nodes => nodes.map(node => {
                    const name = node.querySelector('.pv-skill-category-entity__name-text')?.textContent || null;
                    const endorsements = node.querySelector('.pv-skill-category-entity__endorsement-count')?.textContent || null;
                    return {
                        skillName: name,
                        endorsementCount: endorsements || null
                    };
                })""",
            )

        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"LinkedIn scraping timed out: {exc}") from exc
        finally:
            context.close()
            browser.close()

    def transform_experience(item: Dict[str, Any]) -> Dict[str, Any]:
        start = format_date(item.get("startDate"))
        end = format_date(item.get("endDate"))
        duration = get_duration_in_days(start, end) if start and end else None
        return {
            "title": clean_text(item.get("title")),
            "company": clean_text(item.get("company")),
            "employmentType": clean_text(item.get("employmentType")),
            "location": clean_text(item.get("location")),
            "startDate": start,
            "endDate": end,
            "endDateIsPresent": item.get("endDateIsPresent", False),
            "durationInDays": duration,
            "description": clean_text(item.get("description")),
        }

    def transform_education(item: Dict[str, Any]) -> Dict[str, Any]:
        start = format_date(item.get("startDate"))
        end = format_date(item.get("endDate"))
        return {
            "schoolName": clean_text(item.get("schoolName")),
            "degreeName": clean_text(item.get("degreeName")),
            "fieldOfStudy": clean_text(item.get("fieldOfStudy")),
            "startDate": start,
            "endDate": end,
            "durationInDays": get_duration_in_days(start, end),
        }

    def transform_volunteer(item: Dict[str, Any]) -> Dict[str, Any]:
        start = format_date(item.get("startDate"))
        end = format_date(item.get("endDate"))
        return {
            "title": clean_text(item.get("title")),
            "company": clean_text(item.get("company")),
            "startDate": start,
            "endDate": end,
            "endDateIsPresent": item.get("endDateIsPresent", False),
            "durationInDays": get_duration_in_days(start, end),
            "description": clean_text(item.get("description")),
        }

    def transform_skill(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "skillName": clean_text(item.get("skillName")),
            "endorsementCount": parse_count_text(item.get("endorsementCount")),
        }

    user_profile = {
        "fullName": clean_text(raw_profile.get("fullName")),
        "title": clean_text(raw_profile.get("title")),
        "location": clean_text(raw_profile.get("location")),
        "photo": raw_profile.get("photo"),
        "description": clean_text(raw_profile.get("description")),
        "url": raw_profile.get("url"),
        "connectionsCount": parse_count_text(raw_profile.get("connectionsCountText")),
        "followersCount": parse_count_text(raw_profile.get("followersCountText")),
    }

    experiences = [transform_experience(item) for item in raw_experiences]
    education = [transform_education(item) for item in raw_education]
    volunteer = [transform_volunteer(item) for item in raw_volunteer]
    skills = [transform_skill(item) for item in raw_skills]

    return {
        "userProfile": user_profile,
        "experiences": experiences,
        "education": education,
        "volunteerExperiences": volunteer,
        "skills": skills,
    }


def extract_basic_profile(scraped: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Helper to return sanitized pieces for metrics/profile cards."""
    user_profile = scraped.get("userProfile") or {}
    return user_profile, {
        "skills": (scraped.get("skills") or [])[:10],
        "experiences": (scraped.get("experiences") or [])[:5],
        "education": (scraped.get("education") or [])[:3],
    }


# -------------------- ASYNC VARIANT --------------------
async def scrape_linkedin_profile_async(profile_url: Optional[str] = None, timeout: int = 90) -> Dict[str, Any]:
    """
    Async variant using Playwright's async API to avoid 'Sync API inside asyncio loop' errors.
    """
    li_at = os.getenv("LINKEDIN_SCRAPER_LI_AT")
    if not li_at:
        raise ValueError("LINKEDIN_SCRAPER_LI_AT must be set with the LinkedIn li_at cookie value.")

    target_url = profile_url or os.getenv("LINKEDIN_SCRAPER_PROFILE_URL")
    if not target_url:
        raise ValueError("LinkedIn profile URL not provided. Set LINKEDIN_SCRAPER_PROFILE_URL or pass profile_url.")

    timeout_ms = int(timeout * 1000)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1366,768",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=os.getenv(
                "LINKEDIN_SCRAPER_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
            ),
        )
        await context.add_cookies(
            [
                {
                    "name": "li_at",
                    "value": li_at,
                    "domain": ".www.linkedin.com",
                    "path": "/",
                    "httpOnly": True,
                    "secure": True,
                }
            ]
        )
        page = await context.new_page()
        try:
            await page.goto("https://www.linkedin.com/feed/", wait_until="networkidle", timeout=timeout_ms)
            if page.url.endswith("/login"):
                raise RuntimeError("LinkedIn session cookie expired. Please refresh LINKEDIN_SCRAPER_LI_AT.")

            await page.goto(target_url, wait_until="networkidle", timeout=timeout_ms)
            await page.evaluate(
                """() => new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 500;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 100);
            })"""
            )
            for selector in [
                ".pv-profile-section.pv-about-section .lt-line-clamp__more",
                "#experience-section .pv-profile-section__see-more-inline.link",
                ".pv-profile-section.education-section button.pv-profile-section__see-more-inline",
                ".pv-skill-categories-section [data-control-name='skill_details']",
            ]:
                try:
                    handle = await page.query_selector(selector)
                    if handle:
                        await handle.click()
                except Exception:
                    pass

            await page.wait_for_timeout(500)

            raw_profile = await page.evaluate(
                """() => {
                const profileSection = document.querySelector('.pv-top-card');
                const bulletItems = Array.from(profileSection?.querySelectorAll('.pv-top-card--list-bullet li') || []);

                const connectionsCountText = (bulletItems.find(el => el.textContent?.toLowerCase().includes('connection'))?.textContent || null);
                const followersCountText = (bulletItems.find(el => el.textContent?.toLowerCase().includes('follower'))?.textContent || null);

                const description = document.querySelector('.pv-about__summary-text .lt-line-clamp__raw-line');

                return {
                    fullName: profileSection?.querySelector('.pv-top-card--list li:first-child')?.textContent || null,
                    title: profileSection?.querySelector('h2')?.textContent || null,
                    location: profileSection?.querySelector('.pv-top-card--list.pv-top-card--list-bullet.mt1 li:first-child')?.textContent || null,
                    photo: (profileSection?.querySelector('.pv-top-card__photo') || profileSection?.querySelector('.profile-photo-edit__preview'))?.getAttribute('src') || null,
                    description: description?.textContent || null,
                    url: window.location.href,
                    connectionsCountText,
                    followersCountText
                };
            }"""
            )
            raw_experiences = await page.eval_on_selector_all(
                "#experience-section ul > .ember-view",
                """nodes => nodes.map(node => {
                    const titleElement = node.querySelector('h3');
                    const employmentTypeElement = node.querySelector('span.pv-entity__secondary-title');
                    const companyElement = node.querySelector('.pv-entity__secondary-title');
                    const descriptionElement = node.querySelector('.pv-entity__description');
                    const dateRangeElement = node.querySelector('.pv-entity__date-range span:nth-child(2)');
                    const locationElement = node.querySelector('.pv-entity__location span:nth-child(2)');

                    const dateRangeText = dateRangeElement?.textContent || null;
                    const startDatePart = dateRangeText?.split('–')[0] || null;
                    const endDatePart = dateRangeText?.split('–')[1] || null;
                    const endDateIsPresent = endDatePart?.trim().toLowerCase() === 'present' || false;
                    const endDate = (endDatePart && !endDateIsPresent) ? endDatePart.trim() : 'Present';

                    return {
                        title: titleElement?.textContent || null,
                        employmentType: employmentTypeElement?.textContent || null,
                        company: companyElement?.textContent || null,
                        location: locationElement?.textContent || null,
                        description: descriptionElement?.textContent || null,
                        startDate: startDatePart?.trim() || null,
                        endDate,
                        endDateIsPresent
                    };
                })""",
            )
            raw_education = await page.eval_on_selector_all(
                "#education-section ul > .ember-view",
                """nodes => nodes.map(node => {
                    const schoolNameElement = node.querySelector('h3.pv-entity__school-name');
                    const degreeNameElement = node.querySelector('.pv-entity__degree-name .pv-entity__comma-item');
                    const fieldOfStudyElement = node.querySelector('.pv-entity__fos .pv-entity__comma-item');
                    const dateRangeElement = node.querySelectorAll('.pv-entity__dates time');

                    return {
                        schoolName: schoolNameElement?.textContent || null,
                        degreeName: degreeNameElement?.textContent || null,
                        fieldOfStudy: fieldOfStudyElement?.textContent || null,
                        startDate: dateRangeElement[0]?.textContent || null,
                        endDate: dateRangeElement[1]?.textContent || null
                    };
                })""",
            )
            raw_volunteer = await page.eval_on_selector_all(
                ".pv-profile-section.volunteering-section ul > li.ember-view",
                """nodes => nodes.map(node => {
                    const titleElement = node.querySelector('.pv-entity__summary-info h3');
                    const companyElement = node.querySelector('.pv-entity__summary-info span.pv-entity__secondary-title');
                    const dateRangeElement = node.querySelector('.pv-entity__date-range span:nth-child(2)');
                    const descriptionElement = node.querySelector('.pv-entity__description');

                    const dateRangeText = dateRangeElement?.textContent || null;
                    const startDatePart = dateRangeText?.split('–')[0] || null;
                    const endDatePart = dateRangeText?.split('–')[1] || null;
                    const endDateIsPresent = endDatePart?.trim().toLowerCase() === 'present' || false;
                    const endDate = (endDatePart && !endDateIsPresent) ? endDatePart.trim() : 'Present';

                    return {
                        title: titleElement?.textContent || null,
                        company: companyElement?.textContent || null,
                        description: descriptionElement?.textContent || null,
                        startDate: startDatePart?.trim() || null,
                        endDate,
                        endDateIsPresent
                    };
                })""",
            )
            raw_skills = await page.eval_on_selector_all(
                ".pv-skill-categories-section [data-control-name='skill_details']",
                """nodes => nodes.map(node => {
                    const name = node.querySelector('.pv-skill-category-entity__name-text')?.textContent || null;
                    const endorsements = node.querySelector('.pv-skill-category-entity__endorsement-count')?.textContent || null;
                    return {
                        skillName: name,
                        endorsementCount: endorsements || null
                    };
                })""",
            )
        finally:
            await context.close()
            await browser.close()

    user_profile = {
        "fullName": clean_text(raw_profile.get("fullName")),
        "title": clean_text(raw_profile.get("title")),
        "location": clean_text(raw_profile.get("location")),
        "photo": raw_profile.get("photo"),
        "description": clean_text(raw_profile.get("description")),
        "url": raw_profile.get("url"),
        "connectionsCount": parse_count_text(raw_profile.get("connectionsCountText")),
        "followersCount": parse_count_text(raw_profile.get("followersCountText")),
    }

    def transform_experience(item: Dict[str, Any]) -> Dict[str, Any]:
        start = format_date(item.get("startDate"))
        end = format_date(item.get("endDate"))
        duration = get_duration_in_days(start, end) if start and end else None
        return {
            "title": clean_text(item.get("title")),
            "company": clean_text(item.get("company")),
            "employmentType": clean_text(item.get("employmentType")),
            "location": clean_text(item.get("location")),
            "startDate": start,
            "endDate": end,
            "endDateIsPresent": item.get("endDateIsPresent", False),
            "durationInDays": duration,
            "description": clean_text(item.get("description")),
        }

    def transform_education(item: Dict[str, Any]) -> Dict[str, Any]:
        start = format_date(item.get("startDate"))
        end = format_date(item.get("endDate"))
        return {
            "schoolName": clean_text(item.get("schoolName")),
            "degreeName": clean_text(item.get("degreeName")),
            "fieldOfStudy": clean_text(item.get("fieldOfStudy")),
            "startDate": start,
            "endDate": end,
            "durationInDays": get_duration_in_days(start, end),
        }

    def transform_volunteer(item: Dict[str, Any]) -> Dict[str, Any]:
        start = format_date(item.get("startDate"))
        end = format_date(item.get("endDate"))
        return {
            "title": clean_text(item.get("title")),
            "company": clean_text(item.get("company")),
            "startDate": start,
            "endDate": end,
            "endDateIsPresent": item.get("endDateIsPresent", False),
            "durationInDays": get_duration_in_days(start, end),
            "description": clean_text(item.get("description")),
        }

    def transform_skill(item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "skillName": clean_text(item.get("skillName")),
            "endorsementCount": parse_count_text(item.get("endorsementCount")),
        }

    experiences = [transform_experience(item) for item in raw_experiences]
    education = [transform_education(item) for item in raw_education]
    volunteer = [transform_volunteer(item) for item in raw_volunteer]
    skills = [transform_skill(item) for item in raw_skills]

    return {
        "userProfile": user_profile,
        "experiences": experiences,
        "education": education,
        "volunteerExperiences": volunteer,
        "skills": skills,
    }

