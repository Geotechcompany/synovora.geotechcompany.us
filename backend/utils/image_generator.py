import os
from typing import Optional

from openai import OpenAI
import requests


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for image generation")
    return OpenAI(api_key=api_key)


def generate_post_image(prompt: str, model: Optional[str] = None) -> bytes:
    """
    Generate a LinkedIn-friendly image using OpenAI DALL-E model.

    Args:
        prompt: Description of the desired image.
        model: Optional override for the DALL-E model (dall-e-2 or dall-e-3).

    Returns:
        Raw image bytes (PNG).
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt is required for image generation")

    client = get_openai_client()
    # Default to DALL-E 3 for better quality, fallback to DALL-E 2
    model_name = model or os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3")
    
    # DALL-E 3 only supports certain sizes
    size = "1024x1024" if model_name == "dall-e-3" else "1024x1024"
    quality = "standard" if model_name == "dall-e-3" else None
    
    try:
        # Generate image using OpenAI DALL-E
        response = client.images.generate(
            model=model_name,
            prompt=prompt.strip(),
            size=size,
            quality=quality,
            n=1,
            response_format="url",  # Get URL first, then download
        )
        
        # Get the image URL
        image_url = response.data[0].url
        if not image_url:
            raise ValueError("No image URL returned from OpenAI")
        
        # Download the image
        image_response = requests.get(image_url, timeout=30)
        image_response.raise_for_status()
        
        # Return image bytes
        return image_response.content
        
    except Exception as e:
        raise ValueError(f"Failed to generate image with OpenAI: {str(e)}")



