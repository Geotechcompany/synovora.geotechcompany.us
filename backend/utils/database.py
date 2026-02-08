"""Database module for storing posts and users.

Supports MongoDB (primary), Supabase (Postgres), and file-based fallback.
"""

import os
import json
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from pathlib import Path

from supabase import create_client

_FILE_LOCK = threading.Lock()


def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)


def _read_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return default
    return json.loads(raw)


def _backend_root() -> Path:
    # utils/database.py -> backend/utils -> backend
    return Path(__file__).resolve().parents[1]


class FilePostDatabase:
    """
    Local file-based persistence for posts.
    Intended as a development fallback when MongoDB is unreachable.
    """

    def __init__(self, file_path: Optional[str] = None):
        self.path = Path(file_path) if file_path else (_backend_root() / "posts.json")

    def _load_posts(self) -> list[dict]:
        posts = _read_json_file(self.path, default=[])
        return posts if isinstance(posts, list) else []

    def _save_posts(self, posts: list[dict]) -> None:
        _atomic_write_json(self.path, posts)

    def _get_next_id(self, posts: list[dict]) -> int:
        max_id = 0
        for post in posts:
            try:
                max_id = max(max_id, int(post.get("id", 0)))
            except Exception:
                continue
        return max_id + 1

    def create_post(
        self,
        content: str,
        topic: str,
        status: str = "draft",
        linkedin_post_id: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
    ) -> Dict:
        now = datetime.now().isoformat()
        with _FILE_LOCK:
            posts = self._load_posts()
            post_id = self._get_next_id(posts)
            post = {
                "id": post_id,
                "content": content,
                "topic": topic,
                "status": status,
                "linkedin_post_id": linkedin_post_id,
                "created_at": now,
                "published_at": None,
                "updated_at": now,
                "image_base64": image_base64,
                "image_mime_type": image_mime_type,
                # Keep parity with Mongo responses that include _id
                "_id": f"file:{post_id}",
            }
            posts.insert(0, post)
            self._save_posts(posts)
            return post

    def get_post(self, post_id: int) -> Optional[Dict]:
        with _FILE_LOCK:
            posts = self._load_posts()
            for post in posts:
                if int(post.get("id", -1)) == int(post_id):
                    return post
        return None

    def get_all_posts(self, status: Optional[str] = None) -> List[Dict]:
        with _FILE_LOCK:
            posts = self._load_posts()
            if status:
                return [p for p in posts if p.get("status") == status]
            return posts

    def update_post(self, post_id: int, **kwargs) -> Optional[Dict]:
        now = datetime.now().isoformat()
        with _FILE_LOCK:
            posts = self._load_posts()
            updated = None
            for idx, post in enumerate(posts):
                if int(post.get("id", -1)) == int(post_id):
                    post.update({k: v for k, v in kwargs.items()})
                    post["updated_at"] = now
                    posts[idx] = post
                    updated = post
                    break
            if updated is None:
                return None
            self._save_posts(posts)
            return updated

    def delete_post(self, post_id: int) -> bool:
        with _FILE_LOCK:
            posts = self._load_posts()
            initial = len(posts)
            posts = [p for p in posts if int(p.get("id", -1)) != int(post_id)]
            if len(posts) == initial:
                return False
            self._save_posts(posts)
            return True

    def mark_as_published(self, post_id: int, linkedin_post_id: str) -> Optional[Dict]:
        return self.update_post(
            post_id,
            status="published",
            linkedin_post_id=linkedin_post_id,
            published_at=datetime.now().isoformat(),
        )


class FileUserDatabase:
    """
    Local file-based persistence for Clerk users.
    Intended as a development fallback when MongoDB is unreachable.
    """

    def __init__(self, file_path: Optional[str] = None):
        self.path = Path(file_path) if file_path else (_backend_root() / "clerk_users.json")

    def _load_users(self) -> dict[str, dict]:
        users = _read_json_file(self.path, default={})
        return users if isinstance(users, dict) else {}

    def _save_users(self, users: dict[str, dict]) -> None:
        _atomic_write_json(self.path, users)

    def upsert_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        clerk_user_id = data.get("clerk_user_id")
        if not clerk_user_id:
            raise ValueError("clerk_user_id is required")

        sanitized = {k: v for k, v in data.items() if v is not None}
        now = datetime.now().isoformat()
        with _FILE_LOCK:
            users = self._load_users()
            existing = users.get(clerk_user_id) or {}
            created_at = existing.get("created_at") or sanitized.get("created_at") or now
            merged = {**existing, **sanitized, "created_at": created_at, "updated_at": now}
            merged["_id"] = merged.get("_id") or f"file:{clerk_user_id}"
            users[clerk_user_id] = merged
            self._save_users(users)
            return merged

    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        with _FILE_LOCK:
            users = self._load_users()
            return users.get(clerk_user_id)

    def close(self) -> None:
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_mongo_client():
    """Get MongoDB client. Uses MONGO_DB_URL or MONGODB_URI from env."""
    uri = (os.getenv("MONGO_DB_URL") or os.getenv("MONGODB_URI") or "").strip()
    if not uri:
        raise ValueError("MongoDB is not configured. Set MONGO_DB_URL or MONGODB_URI in .env")
    from pymongo import MongoClient
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client


class MongoPostDatabase:
    """MongoDB-backed database for storing posts."""

    def __init__(self, db_name: Optional[str] = None, collection_name: Optional[str] = None):
        client = _get_mongo_client()
        self.db = client.get_default_database() if not db_name else client[db_name]
        self.collection = self.db[collection_name or "posts"]

    def _next_id(self) -> int:
        with _FILE_LOCK:
            doc = self.collection.find_one(sort=[("id", -1)], projection={"id": 1})
            return (doc["id"] + 1) if doc and doc.get("id") is not None else 1

    def create_post(
        self,
        content: str,
        topic: str,
        status: str = "draft",
        linkedin_post_id: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
        image_url: Optional[str] = None,
        image_storage_path: Optional[str] = None,
    ) -> Dict:
        now = _now_iso()
        post_id = self._next_id()
        doc = {
            "id": post_id,
            "content": content,
            "topic": topic,
            "status": status,
            "linkedin_post_id": linkedin_post_id,
            "image_base64": image_base64,
            "image_mime_type": image_mime_type,
            "image_url": image_url,
            "image_storage_path": image_storage_path,
            "created_at": now,
            "updated_at": now,
            "published_at": None,
        }
        self.collection.insert_one(doc)
        # Return a JSON-serializable copy (insert_one may add _id: ObjectId in-place)
        return {k: v for k, v in doc.items() if k != "_id"}

    def get_post(self, post_id: int) -> Optional[Dict]:
        doc = self.collection.find_one({"id": post_id})
        if doc and "_id" in doc:
            doc = {k: v for k, v in doc.items() if k != "_id"}
        return doc

    def get_all_posts(self, status: Optional[str] = None) -> List[Dict]:
        q = {} if not status else {"status": status}
        cursor = self.collection.find(q).sort("id", -1)
        return [{k: v for k, v in d.items() if k != "_id"} for d in cursor]

    def update_post(self, post_id: int, **kwargs) -> Optional[Dict]:
        payload = {k: v for k, v in kwargs.items() if v is not None}
        payload["updated_at"] = _now_iso()
        from pymongo import ReturnDocument
        result = self.collection.find_one_and_update(
            {"id": post_id},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            return None
        return {k: v for k, v in result.items() if k != "_id"}

    def delete_post(self, post_id: int) -> bool:
        result = self.collection.delete_one({"id": post_id})
        return result.deleted_count > 0

    def mark_as_published(self, post_id: int, linkedin_post_id: str) -> Optional[Dict]:
        return self.update_post(
            post_id,
            status="published",
            linkedin_post_id=linkedin_post_id,
            published_at=_now_iso(),
        )


class MongoUserDatabase:
    """MongoDB-backed storage for Clerk users."""

    def __init__(self, db_name: Optional[str] = None, collection_name: Optional[str] = None):
        client = _get_mongo_client()
        self.db = client.get_default_database() if not db_name else client[db_name]
        self.collection = self.db[collection_name or "clerk_users"]

    def upsert_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        clerk_user_id = data.get("clerk_user_id")
        if not clerk_user_id:
            raise ValueError("clerk_user_id is required")
        existing = self.get_user_by_clerk_id(clerk_user_id)
        created_at = (
            (existing or {}).get("created_at")
            or data.get("created_at")
            or _now_iso()
        )
        sanitized = {k: v for k, v in data.items() if v is not None}
        payload = {
            **sanitized,
            "clerk_user_id": clerk_user_id,
            "created_at": created_at,
            "updated_at": _now_iso(),
        }
        self.collection.update_one(
            {"clerk_user_id": clerk_user_id},
            {"$set": payload},
            upsert=True,
        )
        return self.get_user_by_clerk_id(clerk_user_id) or payload

    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        doc = self.collection.find_one({"clerk_user_id": clerk_user_id})
        if doc and "_id" in doc:
            doc = {k: v for k, v in doc.items() if k != "_id"}
        return doc

    def close(self) -> None:
        return None


def get_supabase_storage_client():
    """
    Return a Supabase client for storage only (no table connection test).
    Use when the main DB is Mongo/file but you still want to upload images to Supabase Storage.
    Returns None if Supabase env vars are not set.
    """
    supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
    supabase_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
    if not supabase_url or not supabase_key:
        return None
    return create_client(supabase_url, supabase_key)


def _get_supabase_client():
    supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
    supabase_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
    if not supabase_url or not supabase_key:
        raise ValueError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (recommended) in .env"
        )
    try:
        client = create_client(supabase_url, supabase_key)
        # Test connection with a simple query
        client.table("posts").select("id").limit(1).execute()
        return client
    except Exception as e:
        error_msg = str(e)
        if "getaddrinfo failed" in error_msg or "ConnectError" in error_msg:
            raise ConnectionError(
                f"Cannot resolve Supabase hostname. Check your network connection and SUPABASE_URL.\n"
                f"URL: {supabase_url}\n"
                f"Error: {error_msg}\n"
                f"Tip: Set PERSISTENCE_ALLOW_FILE_FALLBACK=1 in .env to use local file storage as fallback."
            )
        raise


class PostDatabase:
    """Supabase-backed database for storing posts."""

    def __init__(self, table_name: Optional[str] = None):
        self.client = _get_supabase_client()
        self.table = table_name or os.getenv("SUPABASE_POSTS_TABLE") or "posts"

    def create_post(
        self,
        content: str,
        topic: str,
        status: str = "draft",
        linkedin_post_id: Optional[str] = None,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
        image_url: Optional[str] = None,
        image_storage_path: Optional[str] = None,
    ) -> Dict:
        now = _now_iso()
        payload = {
            "content": content,
            "topic": topic,
            "status": status,
            "linkedin_post_id": linkedin_post_id,
            "image_base64": image_base64,
            "image_mime_type": image_mime_type,
            "image_url": image_url,
            "image_storage_path": image_storage_path,
            "created_at": now,
            "updated_at": now,
            "published_at": None,
        }
        result = self.client.table(self.table).insert(payload).execute()
        if not result.data:
            raise ValueError("Failed to create post in Supabase.")
        return result.data[0]

    def get_post(self, post_id: int) -> Optional[Dict]:
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("id", post_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_all_posts(self, status: Optional[str] = None) -> List[Dict]:
        query = self.client.table(self.table).select("*")
        if status:
            query = query.eq("status", status)
        result = query.order("id", desc=True).execute()
        return result.data or []

    def update_post(self, post_id: int, **kwargs) -> Optional[Dict]:
        payload = {k: v for k, v in kwargs.items() if v is not None}
        payload["updated_at"] = _now_iso()
        result = self.client.table(self.table).update(payload).eq("id", post_id).execute()
        if not result.data:
            return None
        return self.get_post(post_id)

    def delete_post(self, post_id: int) -> bool:
        result = self.client.table(self.table).delete().eq("id", post_id).execute()
        return bool(result.data)

    def mark_as_published(self, post_id: int, linkedin_post_id: str) -> Optional[Dict]:
        return self.update_post(
            post_id,
            status="published",
            linkedin_post_id=linkedin_post_id,
            published_at=_now_iso(),
        )


class UserDatabase:
    """Supabase-backed storage for Clerk users."""

    def __init__(self, table_name: Optional[str] = None):
        self.client = _get_supabase_client()
        self.table = table_name or os.getenv("SUPABASE_USERS_TABLE") or "clerk_users"

    def upsert_user(self, data: Dict[str, Any]) -> Dict[str, Any]:
        clerk_user_id = data.get("clerk_user_id")
        if not clerk_user_id:
            raise ValueError("clerk_user_id is required")

        existing = self.get_user_by_clerk_id(clerk_user_id)
        created_at = (
            (existing or {}).get("created_at")
            or data.get("created_at")
            or _now_iso()
        )

        sanitized = {k: v for k, v in data.items() if v is not None}
        payload = {
            **sanitized,
            "clerk_user_id": clerk_user_id,
            "created_at": created_at,
            "updated_at": _now_iso(),
        }

        result = (
            self.client.table(self.table)
            .upsert(payload, on_conflict="clerk_user_id")
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to upsert user in Supabase.")
        return result.data[0]

    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        result = (
            self.client.table(self.table)
            .select("*")
            .eq("clerk_user_id", clerk_user_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def close(self) -> None:
        return None
