"""
Dropbox storage for post images.
Set DROPBOX_ACCESS_TOKEN in .env (and optionally DROPBOX_IMAGE_FOLDER).
"""
import os
import re
from typing import Optional

# Lazy import so app starts without dropbox if not using it
_dropbox_client = None


def _get_dropbox_client():
    global _dropbox_client
    if _dropbox_client is not None:
        return _dropbox_client
    token = (os.getenv("DROPBOX_ACCESS_TOKEN") or "").strip()
    if not token:
        return None
    try:
        import dropbox
        _dropbox_client = dropbox.Dropbox(token)
        return _dropbox_client
    except Exception:
        return None


def _shared_link_to_direct(url: str) -> str:
    """Convert Dropbox shared link to direct download URL for use in img src."""
    if not url:
        return url
    # https://www.dropbox.com/s/xxxx/file.png?dl=0 -> https://dl.dropboxusercontent.com/s/xxxx/file.png?dl=1
    u = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
    u = re.sub(r"\?dl=0", "?dl=1", u) if "?dl=0" in u else (u + "?dl=1" if "?" not in u else u + "&dl=1")
    return u


def upload_image(
    image_bytes: bytes,
    mime_type: str,
    path_or_name: str,
    folder: Optional[str] = None,
) -> Optional[dict]:
    """
    Upload image to Dropbox and return public direct URL.
    Returns None if Dropbox is not configured or upload fails.
    """
    dbx = _get_dropbox_client()
    if not dbx:
        return None
    folder = (folder or os.getenv("DROPBOX_IMAGE_FOLDER") or "/Synvora/post-images").strip()
    folder = folder.rstrip("/")
    if not path_or_name.startswith("/"):
        path_or_name = f"/{path_or_name}"
    dropbox_path = f"{folder}{path_or_name}"
    try:
        from dropbox.files import WriteMode
        dbx.files_upload(image_bytes, dropbox_path, mode=WriteMode.overwrite)
    except Exception:
        return None
    try:
        from dropbox.exceptions import ApiError
        from dropbox.sharing import SharedLinkSettings
        try:
            link = dbx.sharing_create_shared_link_with_settings(dropbox_path, SharedLinkSettings())
            url = link.url
        except ApiError as e:
            err = getattr(e, "error", None)
            if err and getattr(err, "is_shared_link_already_exists", lambda: False)():
                links = dbx.sharing_list_shared_links(path=dropbox_path, direct_only=True)
                if links.links:
                    url = links.links[0].url
                else:
                    return None
            else:
                return None
        direct_url = _shared_link_to_direct(url)
        return {"url": direct_url, "path": dropbox_path}
    except Exception:
        return None
