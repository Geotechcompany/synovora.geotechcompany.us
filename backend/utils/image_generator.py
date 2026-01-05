import os
from io import BytesIO
from typing import Optional

from huggingface_hub import InferenceClient


HF_MODEL_DEFAULT = "black-forest-labs/FLUX.1-dev"


def get_hf_client() -> InferenceClient:
    api_key = os.getenv("HF_TOKEN")
    if not api_key:
        raise ValueError("HF_TOKEN environment variable is required for image generation")
    provider = os.getenv("HF_PROVIDER", "nebius")
    return InferenceClient(provider=provider, api_key=api_key)


def generate_post_image(prompt: str, model: Optional[str] = None) -> bytes:
    """
    Generate a LinkedIn-friendly image using Hugging Face text-to-image model.

    Args:
        prompt: Description of the desired image.
        model: Optional override for the HF model id.

    Returns:
        Raw image bytes (PNG).
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt is required for image generation")

    client = get_hf_client()
    model_name = model or os.getenv("HF_IMAGE_MODEL", HF_MODEL_DEFAULT)

    image = client.text_to_image(prompt.strip(), model=model_name)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.read()



