"""FastAPI backend for LinkedIn post generator and publisher."""

import os
import base64
import warnings
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
import sys
import asyncio
import re
from typing import Any, Dict

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Playwright needs subprocess support on Windows; ensure we are not on SelectorEventLoop.
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())  # type: ignore[attr-defined]
    except Exception:
        pass

# Disable CrewAI telemetry
os.environ['OTEL_SDK_DISABLED'] = 'true'

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
import secrets
import json
import asyncio
from starlette.concurrency import run_in_threadpool
import jwt
from cryptography.fernet import Fernet
from jwt import PyJWKClient

from agents.linkedin_post_agent import generate_linkedin_post
from agents.profile_intel_agent import analyze_profile_insights
from agents.topic_suggestion_agent import suggest_topics
from utils.database import (
    PostDatabase,
    UserDatabase,
    FilePostDatabase,
    FileUserDatabase,
    MongoPostDatabase,
    MongoUserDatabase,
    MongoAutomationLogStore,
    FileAutomationLogStore,
    SupabaseAutomationLogStore,
    get_supabase_storage_client,
)
from utils.image_generator import generate_post_image

try:
    from langchain_openai import ChatOpenAI
except Exception:
    ChatOpenAI = None
from utils.linkedin_api import LinkedInAPI, exchange_code_for_token, get_oauth_url
from utils.mailer import EmailSender
from utils.profile_scraper import (
    extract_basic_profile,
    is_scraper_configured,
    scrape_linkedin_profile,
)
from utils.trend_fetcher import TrendingTopicFetcher

app = FastAPI(
    title="LinkedIn Post Generator & Publisher",
    description="AI-powered LinkedIn post generation and publishing system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database: try MongoDB first, then Supabase, then file fallback
db = None
user_db = None
automation_logs_store = None
db_init_error = None
_db_backend = None  # "mongo" | "supabase" | "file"

# 1) Try MongoDB if MONGO_DB_URL or MONGODB_URI is set
if (os.getenv("MONGO_DB_URL") or os.getenv("MONGODB_URI")):
    try:
        db = MongoPostDatabase()
        user_db = MongoUserDatabase()
        automation_logs_store = MongoAutomationLogStore()
        _db_backend = "mongo"
        print("\n✅ Using MongoDB for persistence (MONGO_DB_URL / MONGODB_URI).\n")
    except Exception as exc:
        db_init_error = str(exc)
        db = None
        user_db = None
        automation_logs_store = None

# 2) Try Supabase if MongoDB didn't succeed and Supabase is configured
if db is None and (os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY")):
    try:
        db = PostDatabase()
        user_db = UserDatabase()
        automation_logs_store = SupabaseAutomationLogStore()
        _db_backend = "supabase"
        print("\n✅ Using Supabase for persistence.\n")
    except Exception as exc:
        db_init_error = str(exc)
        db = None
        user_db = None
        automation_logs_store = None

# 3) File fallback if enabled
if db is None:
    allow_file_fallback = os.getenv("PERSISTENCE_ALLOW_FILE_FALLBACK", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if allow_file_fallback:
        db = FilePostDatabase(file_path=os.getenv("FILE_POSTS_PATH") or None)
        user_db = FileUserDatabase(file_path=os.getenv("FILE_USERS_PATH") or None)
        automation_logs_store = FileAutomationLogStore()
        _db_backend = "file"
        print("\n⚠️  Database initialization failed. Falling back to local JSON persistence.")
        print("   Data will be stored on disk (development fallback).")
        print(f"   Details: {db_init_error}\n")
    else:
        print("\n❌ Database initialization failed. The API will start in degraded mode.")
        print("   Endpoints that require persistence will return 503 until this is fixed.")
        print("   Tip: set MONGO_DB_URL or SUPABASE_* in .env, or PERSISTENCE_ALLOW_FILE_FALLBACK=1.")
        print(f"   Details: {db_init_error}\n")


def _require_db() -> PostDatabase:
    if db is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Database unavailable",
                "hint": "Fix SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY (or enable file fallback) and restart the server.",
                "details": db_init_error,
            },
        )
    return db


def _require_user_db() -> UserDatabase:
    if user_db is None:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "User database unavailable",
                "hint": "Fix SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY (or enable file fallback) and restart the server.",
                "details": db_init_error,
            },
        )
    return user_db


# --- Clerk JWT verification (for per-user secrets like OpenAI keys) ---
_jwks_clients: Dict[str, PyJWKClient] = {}


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    existing = _jwks_clients.get(jwks_url)
    if existing is not None:
        return existing
    client = PyJWKClient(jwks_url)
    _jwks_clients[jwks_url] = client
    return client


def _require_bearer_token(req: Request) -> str:
    auth_header = req.headers.get("Authorization") or ""
    prefix = "Bearer "
    if not auth_header.startswith(prefix) or len(auth_header) <= len(prefix):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return auth_header[len(prefix) :].strip()


def _verify_clerk_jwt(token: str) -> Dict[str, Any]:
    """
    Verify a Clerk-issued JWT using the token issuer's JWKS.
    """
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    issuer = (unverified or {}).get("iss")
    if not issuer:
        raise HTTPException(status_code=401, detail="Token issuer missing")

    jwks_url = issuer.rstrip("/") + "/.well-known/jwks.json"
    try:
        jwk_client = _get_jwks_client(jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token).key
        audience = os.getenv("CLERK_AUDIENCE") or None
        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={"verify_aud": bool(audience)},
        )
        return decoded
    except HTTPException:
        raise
    except Exception as exc:
        if os.getenv("DEBUG_AUTH", "").strip() in {"1", "true", "yes", "on"}:
            print(f"[auth] JWT verification failed: {exc} (issuer={issuer}, jwks_url={jwks_url})")
        raise HTTPException(status_code=401, detail="Token verification failed")


def _require_clerk_user_id(req: Request) -> str:
    token = _require_bearer_token(req)
    decoded = _verify_clerk_jwt(token)
    sub = decoded.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token subject missing")
    return str(sub)


def _maybe_clerk_user_id(req: Request) -> Optional[str]:
    try:
        return _require_clerk_user_id(req)
    except Exception:
        return None


def _get_fernet() -> Fernet:
    key = os.getenv("APP_ENCRYPTION_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="APP_ENCRYPTION_KEY is not configured on the backend.",
        )
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "APP_ENCRYPTION_KEY is invalid. It must be a 32-byte urlsafe-base64 Fernet key. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ),
        )


def _encrypt_secret(plain: str) -> str:
    f = _get_fernet()
    return f.encrypt(plain.encode("utf-8")).decode("utf-8")


def _decrypt_secret(cipher: str) -> str:
    f = _get_fernet()
    return f.decrypt(cipher.encode("utf-8")).decode("utf-8")


def _get_openai_key_for_user(clerk_user_id: str) -> Optional[str]:
    record = _require_user_db().get_user_by_clerk_id(clerk_user_id) or {}
    encrypted = record.get("openai_api_key_encrypted")
    if not encrypted:
        return None
    try:
        return _decrypt_secret(encrypted)
    except Exception:
        return None


# Pydantic models
class PostGenerateRequest(BaseModel):
    topic: str
    additional_context: Optional[str] = None


class PostPublishRequest(BaseModel):
    post_id: int
    visibility: Optional[str] = "PUBLIC"


class PostUpdateRequest(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None
    image_base64: Optional[str] = None
    image_mime_type: Optional[str] = None
    image_url: Optional[str] = None
    image_storage_path: Optional[str] = None


class PostScheduleRequest(BaseModel):
    scheduled_for: str
    visibility: Optional[str] = "PUBLIC"


class PostImageRequest(BaseModel):
    prompt: str
    model: Optional[str] = None


class TopicSuggestRequest(BaseModel):
    occupation: str
    limit: int = 8


class AutomationPatchRequest(BaseModel):
    enabled: Optional[bool] = None
    frequency: Optional[str] = None  # "daily" | "weekly"
    occupation: Optional[str] = None
    auto_publish: Optional[bool] = None  # when true, auto-created posts are published to LinkedIn; when false, saved as draft
    reset_schedule: Optional[bool] = None  # when true, clear last_auto_run_at so next cron run will process this user


def _storage_bucket() -> str:
    return (os.getenv("SUPABASE_STORAGE_BUCKET") or "linkedinimages").strip()


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip()).strip("-").lower()
    return cleaned or "post"


def _generate_image_prompt_with_llm(
    topic: str, content: str, openai_api_key: Optional[str] = None
) -> Optional[str]:
    """
    Use LLM to generate a single-sentence image prompt that fully reflects the post content.
    Returns None if no API key or on failure.
    """
    api_key = (openai_api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key or ChatOpenAI is None:
        return None
    content_preview = (content or "")[:600].strip()
    topic_line = (topic or "").strip()
    if not topic_line and not content_preview:
        return None
    try:
        llm = ChatOpenAI(
            model=os.getenv("OPENAI_IMAGE_PROMPT_MODEL", "gpt-4o-mini"),
            api_key=api_key,
            temperature=0.4,
            max_tokens=120,
        )
        prompt = f"""Given this LinkedIn post topic and content, write ONE sentence as an image generation prompt for DALL-E.
Describe the visual that best matches the post: the subject, mood, and style (e.g. illustration, diagram, photograph, infographic, minimalist).
The image must have NO text or labels in it. Choose a style that fits the content (workflow → diagram/illustration; story → scene; tips → clean graphic).
Topic: {topic_line or 'N/A'}
Content:
{content_preview or 'N/A'}

Output ONLY the image prompt, nothing else. One sentence only."""
        result = llm.invoke(prompt)
        out = (getattr(result, "content", None) or str(result)).strip()
        if out and len(out) > 10:
            return out
    except Exception:
        pass
    return None


def _build_image_prompt_for_post(
    topic: str, content_snippet: str, openai_api_key: Optional[str] = None
) -> str:
    """
    Build an image prompt fully from the post content. Uses LLM when possible for a dynamic
    prompt; otherwise a content-based fallback (no keyword rules).
    """
    dynamic = _generate_image_prompt_with_llm(topic, content_snippet, openai_api_key)
    if dynamic:
        return dynamic
    subject = (topic or "").strip() or (content_snippet[:100] if content_snippet else "").strip() or "Professional insight"
    return (
        f"Professional visual for LinkedIn: {subject}. "
        "Clean, modern style that matches the post theme. No text or labels in the image. High quality."
    )


def _upload_image(*, image_bytes: bytes, mime_type: str, topic: str, post_id: Optional[int] = None) -> Optional[dict]:
    """
    Upload image to storage. Tries Dropbox first (if DROPBOX_ACCESS_TOKEN set), then Supabase.
    Returns dict with url and path, or None if both unavailable (caller can use base64).
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_topic = _slugify(topic)[:60]
    name = f"{safe_topic}-{post_id or 'new'}-{ts}.png"

    # 1) Dropbox
    if os.getenv("DROPBOX_ACCESS_TOKEN"):
        from utils.dropbox_storage import upload_image as dropbox_upload
        path_slug = f"/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{name}"
        result = dropbox_upload(image_bytes, mime_type, path_slug)
        if result:
            return {"url": result["url"], "path": result["path"], "provider": "dropbox"}

    # 2) Supabase
    database = _require_db()
    client = getattr(database, "client", None) or get_supabase_storage_client()
    if client is not None:
        bucket = _storage_bucket()
        path = f"posts/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{name}"
        try:
            storage = client.storage.from_(bucket)
            storage.upload(
                path,
                image_bytes,
                file_options={
                    "content-type": mime_type,
                    "cache-control": "3600",
                    "upsert": "true",
                },
            )
            public_url = storage.get_public_url(path)
            return {"url": public_url, "path": path, "provider": "supabase"}
        except Exception:
            pass

    return None


def _upload_image_to_supabase(*, image_bytes: bytes, mime_type: str, topic: str, post_id: Optional[int] = None) -> dict:
    """Upload image (Dropbox or Supabase). Raises HTTPException 503 if no storage configured."""
    result = _upload_image(image_bytes=image_bytes, mime_type=mime_type, topic=topic, post_id=post_id)
    if result is not None:
        return result
    raise HTTPException(
        status_code=503,
        detail="Image upload requires DROPBOX_ACCESS_TOKEN or Supabase (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY). Or images will be stored as base64 in the post.",
    )


def _fetch_image_bytes_from_url(url: str) -> tuple[bytes, str]:
    import requests
    res = requests.get(url, timeout=30)
    res.raise_for_status()
    content_type = res.headers.get("content-type") or "image/png"
    return res.content, content_type.split(";")[0].strip()


class PostEmailRequest(BaseModel):
    recipients: List[str]
    subject: Optional[str] = None
    intro: Optional[str] = None
    include_image: bool = False


class ClerkUserPayload(BaseModel):
    clerk_user_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    image_url: Optional[str] = None
    external_id: Optional[str] = None
    last_sign_in_at: Optional[str] = None
    created_at: Optional[str] = None


class OpenAIKeyPayload(BaseModel):
    openai_api_key: str


def _collect_profile_context() -> dict:
    """Attempt to pull profile context from LinkedIn for personalization."""
    context = {}
    if not os.getenv("LINKEDIN_TOKEN") or not os.getenv("PROFILE_URN"):
        return context

    try:
        linkedin_client = LinkedInAPI()
        context = linkedin_client.get_profile_about_details() or {}
    except Exception as exc:
        context = {"error": str(exc)}
    return context


def _derive_user_niche(profile_context: dict, fallback_topic: str) -> str:
    """Build a niche string using profile context and topic fallback."""
    if not profile_context:
        return fallback_topic
    return (
        profile_context.get("headline")
        or profile_context.get("industry")
        or profile_context.get("bio")
        or fallback_topic
    )


def _fetch_trending_topics(niche: str, topic_hint: str) -> dict:
    """Fetch external trend data when the API is configured."""
    result = {"items": [], "error": None}
    fetcher = TrendingTopicFetcher()
    if not fetcher.is_configured():
        result["error"] = "SERPER_API_KEY not configured"
        return result

    try:
        result["items"] = fetcher.fetch_topics(niche=niche, topic_hint=topic_hint)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _compute_content_stats() -> dict:
    """Aggregate basic analytics from stored posts."""
    try:
        posts = _require_db().get_all_posts()
    except Exception as e:
        # If database connection fails, return empty stats
        print(f"Warning: Failed to fetch posts for stats: {e}")
        posts = []
    total = len(posts)
    published_posts = [p for p in posts if p.get("status") == "published"]
    drafts = [p for p in posts if p.get("status") == "draft"]
    scheduled = [p for p in posts if p.get("status") == "scheduled"]

    word_counts = []
    recent_topics = []
    for post in posts[:5]:
        if post.get("topic"):
            recent_topics.append(post["topic"])
        if post.get("content"):
            word_counts.append(len(post["content"].split()))

    avg_word_count = round(sum(word_counts) / len(word_counts), 1) if word_counts else 0
    last_published_at = None
    if published_posts:
        last_published_at = max(
            [
                p.get("published_at") or p.get("updated_at") or p.get("created_at")
                for p in published_posts
                if p.get("published_at") or p.get("updated_at") or p.get("created_at")
            ],
            default=None,
        )

    return {
        "total": total,
        "drafts": len(drafts),
        "published": len(published_posts),
        "scheduled": len(scheduled),
        "avg_word_count": avg_word_count,
        "recent_topics": recent_topics,
        "last_published_at": last_published_at,
    }


def _build_profile_summary(profile_basic: dict, profile_about: dict, metrics: dict, content_stats: dict) -> str:
    """Generate a short natural language summary for UI display."""
    lines = []

    first_name = profile_about.get("first_name") or profile_basic.get("localizedFirstName")
    last_name = profile_about.get("last_name") or profile_basic.get("localizedLastName")
    if first_name or last_name:
        lines.append(f"{first_name or ''} {last_name or ''}".strip())

    headline = profile_about.get("headline")
    if headline:
        lines.append(f"Headline: {headline}")

    industry = profile_about.get("industry")
    if industry:
        lines.append(f"Industry: {industry}")

    followers = metrics.get("followers")
    connections = metrics.get("connections")
    follower_line = []
    if followers is not None:
        follower_line.append(f"{followers:,} followers")
    if connections is not None:
        follower_line.append(f"{connections:,} connections")
    if follower_line:
        lines.append(", ".join(follower_line))

    if content_stats.get("published"):
        lines.append(
            f"{content_stats['published']} published posts this workspace, "
            f"{content_stats['avg_word_count']} avg words."
        )

    if not lines:
        return "Profile details unavailable."

    return " • ".join(lines)


@app.get("/")
async def root():
    """API index endpoint."""
    return {
        "service": "LinkedIn Post Generator & Publisher",
        "status": "running",
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/test/supabase")
async def test_supabase_connection():
    """
    Test Supabase connection and return detailed diagnostics.
    """
    import socket
    from urllib.parse import urlparse
    
    supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
    supabase_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
    
    result = {
        "configured": bool(supabase_url and supabase_key),
        "url": supabase_url if supabase_url else "Not set",
        "has_service_key": bool(os.getenv("SUPABASE_SERVICE_ROLE_KEY")),
        "has_anon_key": bool(os.getenv("SUPABASE_ANON_KEY")),
        "connection_test": {},
        "dns_test": {},
    }
    
    if not supabase_url:
        result["error"] = "SUPABASE_URL is not set in environment variables"
        return result
    
    # Test DNS resolution
    try:
        parsed = urlparse(supabase_url)
        hostname = parsed.hostname
        if hostname:
            result["dns_test"] = {
                "hostname": hostname,
                "resolved": False,
            }
            try:
                ip_address = socket.gethostbyname(hostname)
                result["dns_test"]["resolved"] = True
                result["dns_test"]["ip_address"] = ip_address
            except socket.gaierror as e:
                result["dns_test"]["error"] = f"DNS resolution failed: {str(e)}"
                result["dns_test"]["error_code"] = e.errno
    except Exception as e:
        result["dns_test"]["error"] = f"Failed to parse URL: {str(e)}"
    
    # Test Supabase client connection
    if supabase_url and supabase_key:
        try:
            from utils.database import _get_supabase_client
            client = _get_supabase_client()
            result["connection_test"]["client_created"] = True
            
            # Try a simple query
            try:
                # Test with posts table
                table_name = os.getenv("SUPABASE_POSTS_TABLE", "posts")
                test_query = client.table(table_name).select("id").limit(1).execute()
                result["connection_test"]["query_success"] = True
                result["connection_test"]["table_accessible"] = True
                result["connection_test"]["table_name"] = table_name
            except Exception as query_error:
                result["connection_test"]["query_success"] = False
                result["connection_test"]["query_error"] = str(query_error)
                # Check if it's a table not found error
                if "relation" in str(query_error).lower() or "does not exist" in str(query_error).lower():
                    result["connection_test"]["table_accessible"] = False
                    result["connection_test"]["hint"] = "Table might not exist. Check your Supabase schema."
                else:
                    result["connection_test"]["table_accessible"] = None
                    
        except ConnectionError as e:
            result["connection_test"]["client_created"] = False
            result["connection_test"]["error"] = str(e)
        except Exception as e:
            result["connection_test"]["client_created"] = False
            result["connection_test"]["error"] = f"Unexpected error: {str(e)}"
            result["connection_test"]["error_type"] = type(e).__name__
    
    result["overall_status"] = (
        "connected" if result.get("connection_test", {}).get("query_success") else
        "dns_failed" if not result.get("dns_test", {}).get("resolved") else
        "connection_failed" if result.get("connection_test", {}).get("client_created") == False else
        "table_error" if result.get("connection_test", {}).get("table_accessible") == False else
        "not_configured" if not result.get("configured") else
        "unknown"
    )
    
    return result


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "LinkedIn Post Generator & Publisher",
        "timestamp": datetime.now().isoformat(),
        "db_connected": db is not None,
        "db_error": db_init_error,
    }


@app.post("/generate")
async def generate_post(req: Request, request: PostGenerateRequest):
    """
    Generate a LinkedIn post using AI.
    
    Args:
        request: Post generation request with topic and optional context
        
    Returns:
        Generated post with ID and status
    """
    try:
        if not request.topic or len(request.topic.strip()) == 0:
            raise HTTPException(status_code=400, detail="Topic is required")
        
        profile_context = _collect_profile_context()
        usable_profile_context = (
            profile_context
            if profile_context and not profile_context.get("error")
            else None
        )
        user_niche = _derive_user_niche(profile_context or {}, request.topic)
        trend_payload = _fetch_trending_topics(user_niche, request.topic)
        
        clerk_user_id = _maybe_clerk_user_id(req)
        openai_api_key = _get_openai_key_for_user(clerk_user_id) if clerk_user_id else None

        # Generate post using CrewAI (Gemini/NVIDIA preferred, OpenAI as fallback if available)
        post_content = generate_linkedin_post(
            topic=request.topic,
            additional_context=request.additional_context,
            profile_context=usable_profile_context,
            trending_topics=trend_payload.get("items") or None,
            user_niche=user_niche,
            openai_api_key=openai_api_key,
        )

        image_payload = None
        image_base64 = None
        image_mime_type = None
        image_url = None
        image_storage_path = None
        if os.getenv("HF_TOKEN"):
            try:
                styled_prompt = _build_image_prompt_for_post(
                    request.topic or "",
                    post_content[:600] if post_content else "",
                    openai_api_key=openai_api_key,
                )
                image_bytes = generate_post_image(styled_prompt, None)
                image_mime_type = "image/png"
                uploaded = _upload_image(
                    image_bytes=image_bytes,
                    mime_type=image_mime_type,
                    topic=request.topic,
                )
                if uploaded:
                    image_url = uploaded["url"]
                    image_storage_path = uploaded["path"]
                    image_payload = {
                        "url": image_url,
                        "storage_path": image_storage_path,
                        "mime_type": image_mime_type,
                        "provider": uploaded.get("provider"),
                    }
                else:
                    # No Dropbox/Supabase: store image as base64 in post
                    image_base64 = base64.b64encode(image_bytes).decode("ascii")
                    image_payload = {
                        "mime_type": image_mime_type,
                        "data_url": f"data:{image_mime_type};base64,{image_base64}",
                        "fallback": "Image stored in post (set DROPBOX_ACCESS_TOKEN or Supabase for remote storage).",
                    }
                    # Persist in post for display
                    image_url = None
                    image_storage_path = None
            except Exception as image_error:
                image_payload = {
                    "error": str(image_error)
                }
        
        # Save to database as draft
        post = _require_db().create_post(
            content=post_content,
            topic=request.topic,
            status="draft",
            image_base64=image_base64,
            image_mime_type=image_mime_type,
            image_url=image_url,
            image_storage_path=image_storage_path,
            clerk_user_id=clerk_user_id,
        )
        
        response_payload = {
            "success": True,
            "post": post,
            "message": "Post generated successfully",
            "image": image_payload,
            "intel": {
                "profile_context": profile_context,
                "trend_error": trend_payload.get("error"),
                "trending_topics": trend_payload.get("items"),
            },
        }
        return response_payload
    
    except ValueError as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating post: {str(e)}")


@app.post("/topics/suggest")
async def suggest_topics_endpoint(req: Request, request: TopicSuggestRequest):
    """
    Suggest topic ideas based on user's occupation (work field) + live trends.
    """
    try:
        occupation = (request.occupation or "").strip()
        if not occupation:
            raise HTTPException(status_code=400, detail="occupation is required")

        clerk_user_id = _maybe_clerk_user_id(req)
        openai_api_key = _get_openai_key_for_user(clerk_user_id) if clerk_user_id else None

        # Persist occupation for this Clerk user (optional)
        if clerk_user_id and user_db is not None:
            try:
                _require_user_db().upsert_user(
                    {
                        "clerk_user_id": clerk_user_id,
                        "occupation": occupation,
                        "occupation_set_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception:
                pass

        trend_payload = _fetch_trending_topics(occupation, occupation)

        topics = suggest_topics(
            occupation=occupation,
            trending_topics=trend_payload.get("items") or None,
            limit=request.limit,
            openai_api_key=openai_api_key,
        )

        return {
            "success": True,
            "occupation": occupation,
            "topics": topics,
            "intel": {
                "trend_error": trend_payload.get("error"),
                "trending_topics": trend_payload.get("items"),
            },
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error suggesting topics: {str(e)}")


@app.get("/me/automation")
async def get_automation(req: Request):
    """Get current user's automation settings (enabled, occupation, frequency, last_run_at)."""
    clerk_user_id = _require_clerk_user_id(req)
    _require_user_db()
    record = user_db.get_user_by_clerk_id(clerk_user_id) or {}
    return {
        "enabled": bool(record.get("automation_enabled")),
        "occupation": record.get("occupation"),
        "frequency": (record.get("automation_frequency") or "daily").strip() or "daily",
        "last_run_at": record.get("last_auto_run_at"),
        "auto_publish": bool(record.get("automation_auto_publish")),
    }


@app.patch("/me/automation")
async def patch_automation(req: Request, body: AutomationPatchRequest):
    """Update current user's automation settings. Set occupation before enabling."""
    clerk_user_id = _require_clerk_user_id(req)
    _require_user_db()
    record = user_db.get_user_by_clerk_id(clerk_user_id) or {}
    updates = {}
    if body.enabled is not None:
        if body.enabled and not (record.get("occupation") or "").strip() and not (body.occupation or "").strip():
            raise HTTPException(
                status_code=400,
                detail="Set your profession (occupation) before enabling automation.",
            )
        updates["automation_enabled"] = body.enabled
    if body.frequency is not None:
        if body.frequency not in ("daily", "weekly"):
            raise HTTPException(status_code=400, detail="frequency must be 'daily' or 'weekly'")
        updates["automation_frequency"] = body.frequency
    if body.occupation is not None:
        updates["occupation"] = (body.occupation or "").strip() or None
    if body.auto_publish is not None:
        updates["automation_auto_publish"] = body.auto_publish
    if body.reset_schedule:
        try:
            user_db.clear_last_auto_run_at(clerk_user_id)
        except Exception:
            pass
    if not updates:
        record = user_db.get_user_by_clerk_id(clerk_user_id) or {}
        return {
            "enabled": bool(record.get("automation_enabled")),
            "occupation": record.get("occupation"),
            "frequency": (record.get("automation_frequency") or "daily").strip() or "daily",
            "last_run_at": record.get("last_auto_run_at"),
            "auto_publish": bool(record.get("automation_auto_publish")),
        }
    user_db.upsert_user({"clerk_user_id": clerk_user_id, **updates})
    record = user_db.get_user_by_clerk_id(clerk_user_id) or {}
    return {
        "enabled": bool(record.get("automation_enabled")),
        "occupation": record.get("occupation"),
        "frequency": (record.get("automation_frequency") or "daily").strip() or "daily",
        "last_run_at": record.get("last_auto_run_at"),
        "auto_publish": bool(record.get("automation_auto_publish")),
    }


@app.get("/me/automation/logs")
async def get_automation_logs(req: Request, limit: int = Query(20, ge=1, le=50)):
    """Get automation run logs for the current user."""
    clerk_user_id = _require_clerk_user_id(req)
    if automation_logs_store is None:
        return {"logs": [], "total": 0}
    logs = automation_logs_store.get_logs_for_user(clerk_user_id, limit=limit)
    return {"logs": logs, "total": len(logs)}


def _run_automation_once() -> dict:
    """
    Run auto-create for users with automation enabled. Processes at most
    CRON_AUTOMATION_MAX_USERS_PER_RUN users per invocation (default 1) to avoid OOM on low-memory instances.
    """
    if user_db is None:
        return {"users_processed": 0, "posts_created": 0, "errors": [{"clerk_user_id": "", "error": "User DB unavailable"}]}
    try:
        users = user_db.list_users_with_automation()
    except Exception as e:
        return {"users_processed": 0, "posts_created": 0, "errors": [{"clerk_user_id": "", "error": str(e)}]}
    max_users = max(1, min(10, int(os.getenv("CRON_AUTOMATION_MAX_USERS_PER_RUN", "1"))))
    users = users[:max_users]
    now_iso = datetime.now(timezone.utc).isoformat()
    posts_created = 0
    errors = []
    max_errors = 50
    max_error_len = 200
    for u in users:
        clerk_user_id = u.get("clerk_user_id")
        occupation = (u.get("occupation") or "").strip()
        if not clerk_user_id or not occupation:
            continue
        last_run = u.get("last_auto_run_at")
        freq = (u.get("automation_frequency") or "daily").strip() or "daily"
        if last_run:
            try:
                last_dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                elapsed_seconds = (datetime.now(timezone.utc) - last_dt).total_seconds()
                if freq == "daily" and elapsed_seconds < 23 * 3600:
                    if automation_logs_store:
                        automation_logs_store.append_log(
                            clerk_user_id, now_iso, "skipped", 0,
                            "Already ran in last 23h (daily limit).",
                        )
                    continue  # already ran in last 23h, skip to avoid duplicate same-day post
                if freq == "weekly" and elapsed_seconds < 7 * 24 * 3600:
                    if automation_logs_store:
                        automation_logs_store.append_log(
                            clerk_user_id, now_iso, "skipped", 0,
                            "Already ran in last 7 days (weekly limit).",
                        )
                    continue  # already ran in last 7 days, skip until next week
            except Exception:
                pass
        try:
            trend_payload = _fetch_trending_topics(occupation, occupation)
            topics = suggest_topics(
                occupation=occupation,
                trending_topics=trend_payload.get("items") or None,
                limit=3,
                openai_api_key=_get_openai_key_for_user(clerk_user_id),
            )
            topic = (topics[0] if topics else None) or f"Trending in {occupation}"
            content = generate_linkedin_post(
                topic=topic,
                profile_context=None,
                trending_topics=trend_payload.get("items") or None,
                user_niche=occupation,
                openai_api_key=_get_openai_key_for_user(clerk_user_id),
            )
            image_url_auto = None
            image_base64_auto = None
            image_mime_auto = None
            image_storage_path_auto = None
            if os.getenv("OPENAI_API_KEY") and os.getenv("CRON_AUTOMATION_SKIP_IMAGE", "").strip().lower() not in ("1", "true", "yes", "on"):
                try:
                    openai_key = _get_openai_key_for_user(clerk_user_id)
                    styled_prompt = _build_image_prompt_for_post(
                        topic or "", content[:600] if content else "", openai_api_key=openai_key
                    )
                    image_bytes = generate_post_image(styled_prompt, None)
                    image_mime_auto = "image/png"
                    uploaded = _upload_image(
                        image_bytes=image_bytes,
                        mime_type=image_mime_auto,
                        topic=topic,
                    )
                    if uploaded:
                        image_url_auto = uploaded["url"]
                        image_storage_path_auto = uploaded.get("path")
                    else:
                        image_base64_auto = base64.b64encode(image_bytes).decode("ascii")
                except Exception:
                    pass
            created = _require_db().create_post(
                content=content,
                topic=topic,
                status="draft",
                clerk_user_id=clerk_user_id,
                image_url=image_url_auto,
                image_base64=image_base64_auto,
                image_mime_type=image_mime_auto,
                image_storage_path=image_storage_path_auto,
            )
            posts_created += 1
            user_db.upsert_user({"clerk_user_id": clerk_user_id, "last_auto_run_at": now_iso})
            if automation_logs_store:
                automation_logs_store.append_log(clerk_user_id, now_iso, "success", 1, None)
            auto_publish = bool(u.get("automation_auto_publish"))
            if auto_publish and created and created.get("id") is not None:
                try:
                    linkedin_api = LinkedInAPI()
                    if linkedin_api.validate_token():
                        full_post = _require_db().get_post(created["id"])
                        if full_post and full_post.get("status") == "draft":
                            visibility = (os.getenv("CRON_AUTOMATION_PUBLISH_VISIBILITY") or "PUBLIC").strip().upper()
                            if visibility not in ("PUBLIC", "CONNECTIONS"):
                                visibility = "PUBLIC"
                            result = _publish_post_internal(post=full_post, visibility=visibility)
                            if result.get("success"):
                                _require_db().mark_as_published(
                                    post_id=created["id"],
                                    linkedin_post_id=result.get("post_id", "unknown"),
                                )
                except Exception:
                    pass
        except Exception as exc:
            err_msg = (str(exc))[:max_error_len]
            if len(errors) < max_errors:
                errors.append({"clerk_user_id": clerk_user_id, "error": err_msg})
            if automation_logs_store:
                automation_logs_store.append_log(clerk_user_id, now_iso, "failed", 0, str(exc)[:500])
    return {"users_processed": len(users), "posts_created": posts_created, "errors": errors}


def _run_automation_safe() -> None:
    """Wrapper so background run does not raise; logs are written inside _run_automation_once."""
    try:
        _run_automation_once()
    except Exception:
        pass


@app.post("/cron/run-automation")
@app.get("/cron/run-automation")
async def cron_run_automation():
    """
    Cron-triggered endpoint: run auto-create for users with automation enabled.
    Returns 202 immediately and runs automation in the background so cron services
    (e.g. cron-job.org) do not timeout while trends/AI/publish run.
    """
    if user_db is None:
        raise HTTPException(status_code=503, detail="User DB not available")
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_automation_safe)
    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "message": "Automation started in background."},
    )


@app.post("/generate/image")
async def generate_post_image_endpoint(request: PostImageRequest):
    """
    Generate an illustrative image for a LinkedIn post using OpenAI DALL-E.
    Uploads to Dropbox (if DROPBOX_ACCESS_TOKEN set) or Supabase; otherwise returns 503.
    """
    try:
        prompt_base = request.prompt or "Professional LinkedIn brand visual"
        styled_prompt = f"{prompt_base}. Hyper-realistic, cinematic lighting, 4k professional LinkedIn lifestyle photography."
        image_bytes = generate_post_image(styled_prompt, request.model)
        mime_type = "image/png"
        uploaded = _upload_image(image_bytes=image_bytes, mime_type=mime_type, topic=request.prompt)
        if not uploaded:
            raise HTTPException(
                status_code=503,
                detail="Set DROPBOX_ACCESS_TOKEN or Supabase (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY) for image storage.",
            )
        return {
            "success": True,
            "image_url": uploaded["url"],
            "storage_path": uploaded["path"],
            "mime_type": mime_type,
            "provider": uploaded.get("provider"),
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")


@app.post("/publish")
async def publish_post(request: PostPublishRequest):
    """
    Publish a post to LinkedIn.
    
    Args:
        request: Publish request with post_id and optional visibility
        
    Returns:
        Publication result
    """
    try:
        # Get post from database
        post = _require_db().get_post(request.post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post.get("status") == "published":
            return {
                "success": False,
                "message": "Post is already published",
                "post": post
            }
        
        # Initialize LinkedIn API
        try:
            linkedin_api = LinkedInAPI()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Validate token
        if not linkedin_api.validate_token():
            raise HTTPException(
                status_code=401,
                detail="LinkedIn token is invalid or expired. Please refresh your token."
            )
        
        result = _publish_post_internal(post=post, visibility=request.visibility)
        
        if result.get("success"):
            # Update post status
            _require_db().mark_as_published(
                post_id=request.post_id,
                linkedin_post_id=result.get("post_id", "unknown")
            )
            
            # Get updated post
            updated_post = _require_db().get_post(request.post_id)
            
            return {
                "success": True,
                "message": "Post published successfully",
                "linkedin_result": result,
                "post": updated_post
            }
        else:
            return {
                "success": False,
                "message": "Failed to publish post",
                "error": result.get("error"),
                "details": result.get("details")
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error publishing post: {str(e)}")


def _parse_iso_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="scheduled_for must be an ISO datetime string") from exc
    return parsed


def _publish_post_internal(*, post: dict, visibility: str) -> dict:
    # Initialize LinkedIn API
    linkedin_api = LinkedInAPI()
    if not linkedin_api.validate_token():
        raise HTTPException(status_code=401, detail="LinkedIn token is invalid or expired. Please refresh your token.")

    image_bytes = None
    image_mime_type = post.get("image_mime_type") or "image/png"
    if post.get("image_url"):
        try:
            image_bytes, detected_mime = _fetch_image_bytes_from_url(str(post["image_url"]))
            image_mime_type = detected_mime or image_mime_type
        except Exception:
            image_bytes = None
    elif post.get("image_base64"):
        try:
            image_bytes = base64.b64decode(post["image_base64"])
        except Exception:
            image_bytes = None

    return linkedin_api.post_text_content(
        text=post["content"],
        visibility=visibility,
        image_bytes=image_bytes,
        image_mime_type=image_mime_type,
        image_alt_text=post.get("topic", "Generated visual"),
    )


@app.post("/posts/{post_id}/schedule")
async def schedule_post(post_id: int, request: PostScheduleRequest):
    """
    Schedule a post for future publishing.
    """
    post = _require_db().get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    scheduled_dt = _parse_iso_datetime(request.scheduled_for)
    if scheduled_dt <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="scheduled_for must be in the future")

    updated = _require_db().update_post(
        post_id,
        status="scheduled",
        scheduled_for=scheduled_dt.astimezone(timezone.utc).isoformat(),
        scheduled_visibility=request.visibility or "PUBLIC",
        last_publish_error=None,
    )
    return {"success": True, "post": updated, "message": "Post scheduled"}


async def _scheduler_loop() -> None:
    poll_seconds = int(os.getenv("SCHEDULER_POLL_SECONDS", "20"))
    enabled = os.getenv("SCHEDULER_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return

    while True:
        try:
            # Scheduler requires Supabase (PostDatabase); skip when using file fallback
            database = _require_db()
            if not hasattr(database, "client"):
                await asyncio.sleep(poll_seconds)
                continue

            now_iso = datetime.now(timezone.utc).isoformat()
            # Fetch due scheduled posts
            due = (
                database.client.table(database.table)
                .select("*")
                .eq("status", "scheduled")
                .lte("scheduled_for", now_iso)
                .order("scheduled_for", desc=False)
                .limit(10)
                .execute()
            )
            due_posts = due.data or []
            for post in due_posts:
                post_id = post.get("id")
                if not post_id:
                    continue

                # Claim the job (avoid duplicate publishing across reload/workers)
                claimed = (
                    database.client.table(database.table)
                    .update(
                        {
                            "status": "publishing",
                            "updated_at": now_iso,
                            "publish_attempts": int(post.get("publish_attempts") or 0) + 1,
                        }
                    )
                    .eq("id", post_id)
                    .eq("status", "scheduled")
                    .execute()
                )
                if not claimed.data:
                    continue

                visibility = post.get("scheduled_visibility") or "PUBLIC"
                try:
                    result = _publish_post_internal(post=post, visibility=visibility)
                    if result.get("success"):
                        _require_db().mark_as_published(
                            post_id=int(post_id),
                            linkedin_post_id=result.get("post_id", "unknown"),
                        )
                        _require_db().update_post(
                            int(post_id),
                            last_publish_error=None,
                            scheduled_for=None,
                        )
                    else:
                        _require_db().update_post(
                            int(post_id),
                            status="failed",
                            last_publish_error=str(result.get("error") or result.get("details") or "Unknown error"),
                        )
                except Exception as exc:
                    _require_db().update_post(
                        int(post_id),
                        status="failed",
                        last_publish_error=str(exc),
                    )
        except Exception as exc:
            print(f"Scheduler loop error: {exc}")

        await asyncio.sleep(poll_seconds)


@app.on_event("startup")
async def _start_scheduler() -> None:
    # Run scheduler in-process; disable in environments where you don't want background publishing.
    asyncio.create_task(_scheduler_loop())


@app.get("/posts")
async def list_posts(
    status: Optional[str] = Query(None, description="Filter by status"),
    clerk_user_id: Optional[str] = Query(None, description="Filter by user (for multi-tenant)"),
):
    """
    List all posts, optionally filtered by status and/or clerk_user_id.
    """
    try:
        posts = _require_db().get_all_posts(status=status, clerk_user_id=clerk_user_id)
        return {
            "success": True,
            "count": len(posts),
            "posts": posts
        }
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "ConnectError" in error_msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Database connection failed",
                    "message": "Unable to connect to Supabase. Please check your network connection and Supabase configuration.",
                    "hint": "Verify SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file",
                }
            )
        raise HTTPException(status_code=500, detail=f"Error listing posts: {error_msg}")


@app.get("/profile/insights")
async def profile_insights():
    """
    Return LinkedIn profile analytics, follower counts, and workspace content stats.
    """
    try:
        linkedin_api = LinkedInAPI()
    except ValueError as exc:
        return {
            "success": False,
            "error": str(exc)
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to initialize LinkedIn client: {exc}"
        }

    try:
        profile_basic = linkedin_api.get_profile_info()
        profile_about = linkedin_api.get_profile_about_details()
        metrics = linkedin_api.get_profile_metrics()
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to fetch LinkedIn profile data: {exc}"
        }

    try:
        content_stats = _compute_content_stats()
    except Exception as e:
        print(f"Warning: Failed to compute content stats: {e}")
        content_stats = {
            "published": 0,
            "avg_word_count": 0,
            "last_published_at": None,
            "recent_topics": [],
        }

    profile_payload = {
        "first_name": profile_about.get("first_name") or profile_basic.get("localizedFirstName"),
        "last_name": profile_about.get("last_name") or profile_basic.get("localizedLastName"),
        "headline": profile_about.get("headline"),
        "bio": profile_about.get("bio"),
        "industry": profile_about.get("industry"),
        "vanity_name": profile_about.get("vanity_name"),
        "location": profile_about.get("location"),
    }

    scraped_profile = None
    scrape_error = None

    should_scrape = (
        is_scraper_configured()
        and (
            not profile_payload.get("headline")
            or not profile_payload.get("bio")
            or not metrics.get("followers")
            or not metrics.get("connections")
        )
    )

    scraper_profile_url = os.getenv("LINKEDIN_SCRAPER_PROFILE_URL")
    vanity_name = profile_payload.get("vanity_name")
    if not scraper_profile_url and vanity_name:
        scraper_profile_url = f"https://www.linkedin.com/in/{vanity_name.strip()}/"

    if should_scrape and scraper_profile_url:
        try:
            # Use sync Playwright in a threadpool (Windows-safe; avoids asyncio subprocess issues).
            scraped_profile = await run_in_threadpool(
                scrape_linkedin_profile,
                scraper_profile_url,
                int(os.getenv("LINKEDIN_SCRAPER_TIMEOUT", "90")),
            )
            scraped_user, _ = extract_basic_profile(scraped_profile)

            metrics["followers"] = metrics.get("followers") or scraped_user.get("followersCount")
            metrics["connections"] = metrics.get("connections") or scraped_user.get("connectionsCount")

            profile_payload["headline"] = profile_payload.get("headline") or scraped_user.get("title")
            profile_payload["bio"] = profile_payload.get("bio") or scraped_user.get("description")

            profile_payload["location"] = profile_payload.get("location") or scraped_user.get("location")
        except Exception as exc:
            scraped_profile = None
            scrape_error = str(exc)
    elif should_scrape and not scraper_profile_url:
        scrape_error = "Scraper profile URL not configured."

    if scraped_profile:
        try:
            summary = analyze_profile_insights(
                scraped_profile=scraped_profile,
                metrics=metrics,
                content_stats=content_stats,
            )
        except Exception as exc:
            summary = _build_profile_summary(profile_basic, profile_about, metrics, content_stats)
            scrape_error = f"AI analysis failed: {exc}"
    else:
        summary = _build_profile_summary(profile_basic, profile_about, metrics, content_stats)

    response_timestamp = datetime.now().isoformat()

    return {
        "success": True,
        "profile": profile_payload,
        "metrics": metrics,
        "content": content_stats,
        "summary": summary,
        "scrape": {
            "used": bool(scraped_profile),
            "error": scrape_error,
            "timestamp": response_timestamp if scraped_profile else None,
        },
        "timestamp": response_timestamp
    }


@app.get("/posts/{post_id}")
async def get_post(post_id: int):
    """
    Get a specific post by ID.
    
    Args:
        post_id: Post ID
        
    Returns:
        Post details
    """
    post = _require_db().get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "success": True,
        "post": post
    }


@app.put("/posts/{post_id}")
async def update_post(post_id: int, request: PostUpdateRequest):
    """
    Update a post.
    
    Args:
        post_id: Post ID to update
        request: Update request with optional content and status
        
    Returns:
        Updated post
    """
    post = _require_db().get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    update_data = {}
    if request.content is not None:
        update_data["content"] = request.content
    if request.status is not None:
        update_data["status"] = request.status
    if request.image_base64 is not None:
        update_data["image_base64"] = request.image_base64
    if request.image_mime_type is not None:
        update_data["image_mime_type"] = request.image_mime_type
    if request.image_url is not None:
        update_data["image_url"] = request.image_url
    if request.image_storage_path is not None:
        update_data["image_storage_path"] = request.image_storage_path
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated_post = _require_db().update_post(post_id, **update_data)
    
    return {
        "success": True,
        "message": "Post updated successfully",
        "post": updated_post
    }


@app.post("/posts/{post_id}/email")
async def email_post(post_id: int, request: PostEmailRequest):
    """
    Email a stored LinkedIn draft using the configured SMTP credentials.
    """
    if not request.recipients:
        raise HTTPException(status_code=400, detail="At least one recipient email is required")

    post = _require_db().get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    try:
        mailer = EmailSender()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    subject = request.subject or f"LinkedIn Draft: {post.get('topic', 'New post')}"
    intro_line = request.intro or "Here is the latest LinkedIn draft from your automation workspace."

    text_body = f"""{intro_line}

Topic: {post.get('topic')}

{post.get('content')}

--
LinkedIn Automation
"""

    html_body = f"""
    <p>{intro_line}</p>
    <p><strong>Topic:</strong> {post.get('topic')}</p>
    <p style="white-space:pre-line; font-family: 'Segoe UI', Arial, sans-serif;">{post.get('content')}</p>
    <p style="color:#94a3b8;font-size:12px;">Sent via LinkedIn Automation</p>
    """

    attachments = []
    if request.include_image and post.get("image_base64"):
        try:
            image_bytes = base64.b64decode(post["image_base64"])
            attachments.append(
                {
                    "filename": f"{post.get('topic', 'linkedin')}.png",
                    "content": image_bytes,
                    "mime_type": post.get("image_mime_type") or "image/png",
                }
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to decode stored image: {exc}")

    try:
        mailer.send_email(
            recipients=request.recipients,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            attachments=attachments,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}")

    return {
        "success": True,
        "message": f"Email sent to {len(request.recipients)} recipient(s)"
    }


@app.delete("/posts/{post_id}")
async def delete_post(post_id: int):
    """
    Delete a post.
    
    Args:
        post_id: Post ID to delete
        
    Returns:
        Deletion result
    """
    post = _require_db().get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    success = _require_db().delete_post(post_id)
    
    if success:
        return {
            "success": True,
            "message": "Post deleted successfully"
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to delete post")


@app.get("/auth/status")
async def auth_status(clerk_user_id: Optional[str] = Query(None)):
    """
    Check LinkedIn authentication status.
    
    Returns:
        Authentication status and profile info if authenticated
    """
    cache_seconds = int(os.getenv("LINKEDIN_STATUS_CACHE_SECONDS", "300"))
    now_iso = datetime.now(timezone.utc).isoformat()

    cached_payload = None
    cached_last_checked = None
    if clerk_user_id and user_db is not None:
        try:
            record = user_db.get_user_by_clerk_id(clerk_user_id)
        except Exception:
            record = None

        if record:
            cached_last_checked = record.get("linkedin_last_checked_at")
            cached_payload = {
                "authenticated": bool(record.get("linkedin_connected")),
                "profile": record.get("linkedin_profile"),
                "message": record.get("linkedin_status_message"),
                "cached": True,
                "last_checked_at": cached_last_checked,
            }

            def _is_fresh(ts: Optional[str]) -> bool:
                if not ts:
                    return False
                try:
                    parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    parsed_utc = parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
                    return (datetime.now(timezone.utc) - parsed_utc).total_seconds() < cache_seconds
                except Exception:
                    return False

            if _is_fresh(cached_last_checked):
                return cached_payload

    try:
        linkedin_api = LinkedInAPI()
        
        if linkedin_api.validate_token():
            profile = linkedin_api.get_profile_info()
            if clerk_user_id and user_db is not None:
                try:
                    user_db.upsert_user(
                        {
                            "clerk_user_id": clerk_user_id,
                            "linkedin_connected": True,
                            "linkedin_profile": profile,
                            "linkedin_last_checked_at": now_iso,
                            "linkedin_status_message": "Connected",
                        }
                    )
                except Exception:
                    pass
            return {
                "authenticated": True,
                "profile": profile,
                "cached": False,
                "last_checked_at": now_iso,
            }
        else:
            if clerk_user_id and user_db is not None:
                try:
                    user_db.upsert_user(
                        {
                            "clerk_user_id": clerk_user_id,
                            "linkedin_connected": False,
                            "linkedin_profile": None,
                            "linkedin_last_checked_at": now_iso,
                            "linkedin_status_message": "Token is invalid or expired",
                        }
                    )
                except Exception:
                    pass
            return {
                "authenticated": False,
                "message": "Token is invalid or expired",
                "cached": False,
                "last_checked_at": now_iso,
            }
    except ValueError:
        # If credentials are missing but we have a cached state, prefer returning cached.
        if cached_payload:
            return {
                **cached_payload,
                "message": cached_payload.get("message") or "Using cached LinkedIn status (credentials not loaded).",
            }
        return {
            "authenticated": False,
            "message": "LinkedIn credentials not configured"
        }
    except Exception as e:
        print(f"Auth Check Error: {str(e)}")  # Log detailed error
        if cached_payload:
            return {
                **cached_payload,
                "message": cached_payload.get("message") or f"Using cached LinkedIn status (live check failed: {e}).",
            }
        return {
            "authenticated": False,
            "message": f"Error checking auth: {str(e)}"
        }


@app.post("/users/sync")
async def sync_clerk_user(payload: ClerkUserPayload):
    """
    Store or update a Clerk user record in MongoDB.
    """
    try:
        user = _require_user_db().upsert_user(payload.model_dump())
        return {
            "success": True,
            "user": user
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "ConnectError" in error_msg:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Database connection failed",
                    "message": "Unable to connect to Supabase. Please check your network connection.",
                    "hint": "Verify SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file",
                }
            )
        raise HTTPException(status_code=500, detail=f"Error syncing user: {error_msg}")


@app.get("/users/openai-key/status")
async def get_openai_key_status(req: Request):
    """
    Returns whether the current Clerk user has an OpenAI API key stored.
    """
    clerk_user_id = _require_clerk_user_id(req)
    record = _require_user_db().get_user_by_clerk_id(clerk_user_id) or {}
    encrypted = record.get("openai_api_key_encrypted")
    return {
        "has_key": bool(encrypted),
        "last4": record.get("openai_api_key_last4"),
        "set_at": record.get("openai_api_key_set_at"),
    }


@app.post("/users/openai-key")
async def set_openai_key(req: Request, payload: OpenAIKeyPayload):
    """
    Store an OpenAI API key for the current Clerk user (encrypted at rest in Supabase).
    """
    clerk_user_id = _require_clerk_user_id(req)
    api_key = (payload.openai_api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="openai_api_key is required")

    encrypted = _encrypt_secret(api_key)
    last4 = api_key[-4:] if len(api_key) >= 4 else api_key
    now_iso = datetime.now(timezone.utc).isoformat()

    _require_user_db().upsert_user(
        {
            "clerk_user_id": clerk_user_id,
            "openai_api_key_encrypted": encrypted,
            "openai_api_key_last4": last4,
            "openai_api_key_set_at": now_iso,
        }
    )

    return {
        "success": True,
        "has_key": True,
        "last4": last4,
        "set_at": now_iso,
    }


@app.get("/auth/url")
async def get_auth_url(clerk_user_id: Optional[str] = Query(None)):
    """
    Get LinkedIn OAuth authorization URL.
    
    Returns:
        OAuth URL for user to authorize the app
    """
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/auth/callback")
    
    if not client_id:
        raise HTTPException(
            status_code=400,
            detail="LINKEDIN_CLIENT_ID not configured. Please set it in .env"
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    auth_url, _ = get_oauth_url(client_id, redirect_uri, state=state)

    response = JSONResponse(
        {
            "success": True,
            "auth_url": auth_url,
            "message": "Visit this URL to authorize the app",
        }
    )
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax")
    if clerk_user_id:
        response.set_cookie("oauth_clerk_user_id", clerk_user_id, httponly=True, samesite="lax")
    return response


@app.get("/auth/connect")
async def connect_linkedin(clerk_user_id: Optional[str] = Query(None)):
    """
    Redirect to LinkedIn OAuth authorization page.
    """
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/auth/callback")
    
    if not client_id:
        raise HTTPException(
            status_code=400,
            detail="LINKEDIN_CLIENT_ID not configured. Please set it in .env"
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    auth_url, _ = get_oauth_url(client_id, redirect_uri, state=state)

    response = RedirectResponse(url=auth_url)
    response.set_cookie("oauth_state", state, httponly=True, samesite="lax")
    if clerk_user_id:
        response.set_cookie("oauth_clerk_user_id", clerk_user_id, httponly=True, samesite="lax")
    return response


@app.get("/auth/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
):
    """
    Handle LinkedIn OAuth callback.
    
    Args:
        code: Authorization code from LinkedIn
        state: State parameter for CSRF protection
        error: Error message if authorization failed
    """
    if error:
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: red;">❌ Authorization Failed</h1>
                    <p>Error: {error}</p>
                    <a href="/" style="color: blue;">Return to Dashboard</a>
                </body>
            </html>
            """,
            status_code=400
        )
    
    if not code:
        return HTMLResponse(
            content="""
            <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: red;">❌ Missing Authorization Code</h1>
                    <p>No authorization code received from LinkedIn.</p>
                    <a href="/" style="color: blue;">Return to Dashboard</a>
                </body>
            </html>
            """,
            status_code=400
        )
    
    # Verify state (CSRF protection) using cookies (safe across reload/multi-process).
    stored_state = request.cookies.get("oauth_state")
    stored_clerk_user_id = request.cookies.get("oauth_clerk_user_id")

    if not stored_state or state != stored_state:
        frontend_url = (os.getenv("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: red;">❌ Invalid State Parameter</h1>
                    <p>Security validation failed. Please try again.</p>
                    <a href="{frontend_url}/" style="color: blue;">Return to Dashboard</a>
                </body>
            </html>
            """,
            status_code=400,
        )
    
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip('"').strip("'")
    redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/auth/callback")
    
    if not client_id or not client_secret:
        return HTMLResponse(
            content="""
            <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: red;">❌ Configuration Error</h1>
                    <p>LinkedIn credentials not configured properly.</p>
                    <a href="/" style="color: blue;">Return to Dashboard</a>
                </body>
            </html>
            """,
            status_code=500
        )
    
    try:
        # Exchange code for token
        token_data = exchange_code_for_token(code, client_id, client_secret, redirect_uri)
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 5184000)  # Default 60 days
        
        if not access_token:
            raise Exception("No access token in response")
        
        # Get profile info to get URN
        linkedin_api = LinkedInAPI(access_token=access_token)
        # For OIDC, we only need the profile ID to construct the URN if it's not already there
        # But validate_token or get_profile_info is called next.
        try:
            profile = linkedin_api.get_profile_info()
            # Try different ways to get the profile ID/URN
            profile_id = profile.get('sub') or profile.get('id') or ''
            
            # OIDC returns 'given_name', 'family_name', 'picture' etc.
            # Legacy returns 'localizedFirstName' etc.
            
            if profile_id:
                profile_urn = f"urn:li:person:{profile_id}"
            else:
                profile_urn = "urn:li:person:SET_MANUALLY"
        except Exception as e:
            profile_urn = "urn:li:person:SET_MANUALLY"
            print(f"Warning: Could not fetch profile info: {e}")
        
        # Update .env file with new token and URN
        base_dir = Path(__file__).parent
        env_path = base_dir / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                env_content = f.read()
            
            # Update or add LINKEDIN_TOKEN
            import re
            if re.search(r'^LINKEDIN_TOKEN=', env_content, re.MULTILINE):
                env_content = re.sub(
                    r'^LINKEDIN_TOKEN=.*$',
                    f'LINKEDIN_TOKEN={access_token}',
                    env_content,
                    flags=re.MULTILINE
                )
            else:
                env_content += f"\nLINKEDIN_TOKEN={access_token}\n"
            
            # Update or add PROFILE_URN
            if re.search(r'^PROFILE_URN=', env_content, re.MULTILINE):
                env_content = re.sub(
                    r'^PROFILE_URN=.*$',
                    f'PROFILE_URN={profile_urn}',
                    env_content,
                    flags=re.MULTILINE
                )
            else:
                env_content += f"\nPROFILE_URN={profile_urn}\n"
            
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content)
            
            # Reload environment variables
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
        
        # Persist LinkedIn connection status for this Clerk user (to avoid UI delays)
        if stored_clerk_user_id and user_db is not None:
            try:
                user_db.upsert_user(
                    {
                        "clerk_user_id": stored_clerk_user_id,
                        "linkedin_connected": True,
                        "linkedin_profile": profile,
                        "linkedin_last_checked_at": datetime.now(timezone.utc).isoformat(),
                        "linkedin_status_message": "Connected",
                    }
                )
            except Exception:
                pass

        # Clear cookies after successful callback
        frontend_url = (os.getenv("FRONTEND_URL") or "http://localhost:5173").rstrip("/")
        redirect_target = f"{frontend_url}/"

        response = HTMLResponse(
            content=f"""
            <html>
                <head>
                    <meta http-equiv="refresh" content="2;url={redirect_target}">
                    <title>LinkedIn Connected</title>
                </head>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: green;">✅ Successfully Connected to LinkedIn!</h1>
                    <p>Your LinkedIn account has been connected.</p>
                    <p><strong>Token expires in:</strong> {expires_in // 86400} days</p>
                    <p style="color:#64748b;margin-top:16px;">Redirecting you back to the dashboard…</p>
                    <a href="{redirect_target}" style="display: inline-block; margin-top: 20px; padding: 10px 20px; background: #0077b5; color: white; text-decoration: none; border-radius: 5px;">Go to Dashboard</a>
                    <script>
                      setTimeout(function () {{
                        window.location.href = "{redirect_target}";
                      }}, 1200);
                    </script>
                </body>
            </html>
            """
        )
        response.delete_cookie("oauth_state")
        response.delete_cookie("oauth_clerk_user_id")
        return response
    
    except Exception as e:
        return HTMLResponse(
            content=f"""
            <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: red;">❌ Connection Failed</h1>
                    <p>Error: {str(e)}</p>
                    <a href="/" style="color: blue;">Return to Dashboard</a>
                </body>
            </html>
            """,
            status_code=500
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

