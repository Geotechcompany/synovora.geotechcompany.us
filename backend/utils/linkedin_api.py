"""LinkedIn API integration for posting content."""

import os
import json
from typing import Dict, Optional
from urllib.parse import quote

import requests


class LinkedInAPI:
    """Handles LinkedIn API operations for posting content."""
    
    def __init__(self, access_token: Optional[str] = None, profile_urn: Optional[str] = None):
        """
        Initialize LinkedIn API client.
        
        Args:
            access_token: LinkedIn OAuth 2.0 access token
            profile_urn: LinkedIn profile URN (e.g., urn:li:person:abc123xyz)
        """
        self.access_token = access_token or os.getenv("LINKEDIN_TOKEN")
        self.profile_urn = profile_urn or os.getenv("PROFILE_URN")
        
        if not self.access_token:
            raise ValueError("LinkedIn access token is required. Set LINKEDIN_TOKEN in .env")
        if not self.profile_urn:
            raise ValueError("LinkedIn profile URN is required. Set PROFILE_URN in .env")
        
        self.base_url = "https://api.linkedin.com/v2"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

    @property
    def profile_id(self) -> Optional[str]:
        """Extract the profile identifier from the URN."""
        if not self.profile_urn:
            return None
        parts = self.profile_urn.split(":")
        return parts[-1] if parts else None
    
    def get_profile_info(self) -> Dict:
        """Get authenticated user's profile information."""
        # Try OIDC userinfo endpoint first (standard for new apps)
        try:
            # OIDC endpoint doesn't like Restli headers usually, and typically is just /userinfo
            oidc_headers = self.headers.copy()
            if "X-Restli-Protocol-Version" in oidc_headers:
                del oidc_headers["X-Restli-Protocol-Version"]
                
            response = requests.get(
                f"{self.base_url}/userinfo",
                headers=oidc_headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"OIDC Userinfo check failed: {response.status_code} {response.text}")
        except Exception as e:
            print(f"OIDC Userinfo check error: {e}")
            pass
            
        # Fallback to legacy /me endpoint
        try:
            response = requests.get(
                f"{self.base_url}/me",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                print(f"Profile fetch failed: {e.response.status_code} {e.response.text}")
            raise Exception(f"Failed to get profile info: {str(e)}")

    def get_profile_about_details(self) -> Dict[str, Optional[str]]:
        """
        Fetch enriched profile data including headline and summary.

        Returns:
            Dictionary with headline, summary/bio, industry, and raw payload.
        """
        projection = (
            "(id,localizedFirstName,localizedLastName,localizedHeadline,"
            "localizedSummary,industryName,vanityName)"
        )
        detail: Dict[str, Optional[str]] = {
            "first_name": None,
            "last_name": None,
            "headline": None,
            "bio": None,
            "industry": None,
            "vanity_name": None,
            "raw": None,
        }

        errors = []

        # Attempt to expand /me projection first
        try:
            response = requests.get(
                f"{self.base_url}/me?projection={projection}",
                headers=self.headers,
                timeout=15,
            )
            if response.status_code == 200:
                payload = response.json()
                detail.update(
                    {
                        "first_name": payload.get("localizedFirstName"),
                        "last_name": payload.get("localizedLastName"),
                        "headline": payload.get("localizedHeadline"),
                        "bio": payload.get("localizedSummary") or payload.get("summary"),
                        "industry": payload.get("industryName"),
                        "vanity_name": payload.get("vanityName"),
                        "raw": payload,
                    }
                )
                return detail
            errors.append(f"/me projection: {response.status_code} {response.text}")
        except Exception as exc:  # Broad to keep generating posts even if call fails
            errors.append(f"/me projection error: {exc}")

        # Fallback to identityProfiles endpoint
        if self.profile_urn:
            encoded_urn = quote(self.profile_urn, safe="")
            identity_url = f"https://api.linkedin.com/rest/identityProfiles/{encoded_urn}"
            projection_params = {
                "projection": "(headline,industryName,summary)",
            }
            try:
                response = requests.get(
                    identity_url,
                    headers={
                        **self.headers,
                        "LinkedIn-Version": "202401",
                        "Accept": "application/json",
                    },
                    params=projection_params,
                    timeout=15,
                )
                if response.status_code == 200:
                    payload = response.json()
                    headline = payload.get("headline", {})
                    summary = payload.get("summary", {})
                    # Each field can be localized -> pick english fallback
                    def resolve_localized(field: Dict) -> Optional[str]:
                        if not isinstance(field, dict):
                            return field
                        preferred = field.get("localized", {})
                        if isinstance(preferred, dict):
                            # Return first locale entry
                            for value in preferred.values():
                                if value:
                                    return value
                        return field.get("preferredLocale", None)

                    detail.update(
                        {
                            "headline": resolve_localized(headline) or detail["headline"],
                            "bio": resolve_localized(summary) or detail["bio"],
                            "industry": payload.get("industryName") or detail["industry"],
                            "raw": payload,
                        }
                    )
                    return detail
                errors.append(
                    f"identityProfiles fallback: {response.status_code} {response.text}"
                )
            except Exception as exc:
                errors.append(f"identityProfiles fallback error: {exc}")

        detail["raw"] = {"errors": errors}
        return detail

    def _extract_network_response_value(self, payload: Dict) -> Optional[int]:
        """Extract numeric value from various LinkedIn network size payload shapes."""
        if not payload:
            return None

        candidate_keys = (
            "firstDegreeSize",
            "size",
            "value",
            "total",
            "count",
        )

        for key in candidate_keys:
            value = payload.get(key)
            if isinstance(value, int):
                return value
            if isinstance(value, dict):
                for nested_val in value.values():
                    if isinstance(nested_val, int):
                        return nested_val

        elements = payload.get("elements")
        if isinstance(elements, list):
            for element in elements:
                if isinstance(element, dict):
                    extracted = self._extract_network_response_value(element)
                    if isinstance(extracted, int):
                        return extracted
        return None

    def _get_network_size(self, edge_type: str) -> Optional[int]:
        """
        Query LinkedIn networkSizes endpoint for a specific edge type.

        Args:
            edge_type: LinkedIn edge type identifier (e.g., FIRST_DEGREE_CONNECTIONS)

        Returns:
            Integer size if available, otherwise None.
        """
        if not self.profile_urn:
            return None

        encoded_urn = quote(self.profile_urn, safe="")

        endpoints = [
            {
                "url": f"{self.base_url}/networkSizes/{encoded_urn}",
                "headers": self.headers,
                "params": {"edgeType": edge_type},
            },
            {
                "url": f"https://api.linkedin.com/rest/networkSizes/{encoded_urn}",
                "headers": {
                    "Authorization": f"Bearer {self.access_token}",
                    "Accept": "application/json",
                    "LinkedIn-Version": "202401",
                },
                "params": {"edgeType": edge_type},
            },
        ]

        for endpoint in endpoints:
            try:
                response = requests.get(
                    endpoint["url"],
                    headers=endpoint["headers"],
                    params=endpoint["params"],
                    timeout=10,
                )
                if response.status_code != 200:
                    continue
                data = response.json()
                extracted = self._extract_network_response_value(data)
                if isinstance(extracted, int):
                    return extracted
            except Exception:
                continue

        return None

    def get_profile_metrics(self) -> Dict[str, Optional[int]]:
        """Return follower/connection counts when accessible."""
        metrics = {
            "connections": 0,
            "followers": 0,
        }

        # FIRST_DEGREE_CONNECTIONS is the documented edge type for member connections
        connections = self._get_network_size("FIRST_DEGREE_CONNECTIONS")
        if isinstance(connections, int):
            metrics["connections"] = connections

        # Followers may be returned via MEMBER_FOLLOWED_BY_MEMBER or fallback to CompanyFollowedByMember
        followers = (
            self._get_network_size("MEMBER_FOLLOWED_BY_MEMBER")
            or self._get_network_size("MemberFollowedByMember")
            or self._get_network_size("CompanyFollowedByMember")
        )
        if isinstance(followers, int):
            metrics["followers"] = followers

        return metrics
    
    def _upload_image_asset(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Upload an image to LinkedIn and return the asset URN."""
        register_payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": self.profile_urn,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        register_response = requests.post(
            f"{self.base_url}/assets?action=registerUpload",
            headers=self.headers,
            data=json.dumps(register_payload)
        )
        register_response.raise_for_status()
        register_data = register_response.json()
        upload_mechanism = register_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]
        upload_url = upload_mechanism["uploadUrl"]
        asset_urn = register_data["value"]["asset"]
        
        upload_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": mime_type
        }
        upload_response = requests.put(
            upload_url,
            data=image_bytes,
            headers=upload_headers
        )
        upload_response.raise_for_status()
        return asset_urn
    
    def post_text_content(self, text: str, visibility: str = "PUBLIC", image_bytes: Optional[bytes] = None,
                          image_alt_text: Optional[str] = None, image_mime_type: str = "image/png") -> Dict:
        """
        Publish a text-only LinkedIn post using the UGC Posts API.
        
        Args:
            text: Body of the post.
            visibility: Member network visibility (PUBLIC or CONNECTIONS).
        
        Returns:
            Dictionary describing success/error state and LinkedIn response data.
        """
        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return {"success": False, "error": "Post text is required"}
        
        normalized_visibility = (visibility or "PUBLIC").upper()
        if normalized_visibility not in {"PUBLIC", "CONNECTIONS"}:
            normalized_visibility = "PUBLIC"
        
        media_entries = None
        share_category = "NONE"
        
        if image_bytes:
            try:
                asset_urn = self._upload_image_asset(image_bytes, image_mime_type)
                share_category = "IMAGE"
                media_entries = [{
                    "status": "READY",
                    "description": {"text": (image_alt_text or cleaned_text)[:200]},
                    "media": asset_urn,
                    "title": {"text": image_alt_text or "Generated visual"}
                }]
            except Exception as image_exc:
                print(f"Image upload failed, falling back to text-only post: {image_exc}")
                share_category = "NONE"
                media_entries = None
        
        payload = {
            "author": self.profile_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": cleaned_text},
                    "shareMediaCategory": share_category
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": normalized_visibility
            }
        }
        if media_entries:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_entries
        
        try:
            response = requests.post(
                f"{self.base_url}/ugcPosts",
                headers=self.headers,
                data=json.dumps(payload)
            )
            if response.status_code in (200, 201):
                data = response.json()
                post_id = data.get("id") or data.get("entityUrn")
                return {
                    "success": True,
                    "post_id": post_id,
                    "details": data
                }
            
            error_info = {
                "status_code": response.status_code,
                "response": response.text
            }
            return {
                "success": False,
                "error": "LinkedIn API returned an error",
                "details": error_info
            }
        except requests.exceptions.RequestException as exc:
            return {
                "success": False,
                "error": "Failed to contact LinkedIn API",
                "details": str(exc)
            }

    def validate_token(self) -> bool:
        """
        Validate if the access token is still valid.
        
        Returns:
            True if token is valid, False otherwise
        """
        try:
            self.get_profile_info()
            return True
        except Exception as e:
            print(f"Token validation failed: {str(e)}")
            return False


def get_oauth_url(client_id: str, redirect_uri: str, state: str = None, scopes: list = None):
    """
    Generate LinkedIn OAuth 2.0 authorization URL.
    
    Args:
        client_id: LinkedIn app client ID
        redirect_uri: Redirect URI after authorization
        state: Optional state parameter for CSRF protection
        scopes: List of requested scopes (default: w_member_social for posting)
        
    Returns:
        Tuple of (OAuth authorization URL, state)
    """
    if scopes is None:
        # Use OIDC scopes + posting permission (most modern apps don't have r_liteprofile)
        scopes = ["w_member_social", "openid", "profile", "email"]
    
    if state is None:
        import secrets
        state = secrets.token_urlsafe(32)
    
    scope_string = " ".join(scopes)
    
    base_url = "https://www.linkedin.com/oauth/v2/authorization"
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": scope_string
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}", state


def exchange_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict:
    """
    Exchange authorization code for access token.
    
    Args:
        code: Authorization code from OAuth callback
        client_id: LinkedIn app client ID
        client_secret: LinkedIn app client secret
        redirect_uri: Redirect URI used in authorization
        
    Returns:
        Dictionary with access_token, expires_in, and other token info
    """
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(token_url, data=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to exchange code for token: {str(e)}")


if __name__ == "__main__":
    # Test LinkedIn API (requires valid token)
    print("Testing LinkedIn API...")
    
    try:
        api = LinkedInAPI()
        
        # Validate token
        print("Validating token...")
        if api.validate_token():
            print("✅ Token is valid")
            
            # Get profile info
            profile = api.get_profile_info()
            print(f"✅ Profile: {profile.get('localizedFirstName', 'N/A')} {profile.get('localizedLastName', 'N/A')}")
            
            # Test post (commented out to avoid accidental posting)
            # test_post = "This is a test post from the LinkedIn automation system. 🚀"
            # result = api.post_text_content(test_post)
            # print(f"Post result: {result}")
        else:
            print("❌ Token is invalid or expired")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

