import io
from typing import Tuple
from PIL import Image
import imagehash


ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
MAX_IMAGE_SIZE_BYTES = 2 * 1024 * 1024  # 2MB


def compute_image_phash(image_bytes: bytes) -> Tuple[str, str]:
    """
    Compute 64-bit perceptual hash (pHash) from image bytes.
    Validates size and image integrity.
    Returns (hex_hash, format_name).
    """
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise ValueError(f"Image exceeds maximum size limit of {MAX_IMAGE_SIZE_BYTES // (1024*1024)}MB")

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            fmt = (img.format or "PNG").upper()
            if fmt not in ALLOWED_FORMATS:
                raise ValueError(f"Unsupported image format: {fmt}. Allowed: {', '.join(ALLOWED_FORMATS)}")

            # Convert to RGB to avoid alpha/mode issues during pHash computation
            rgb_img = img.convert("RGB")
            h = imagehash.phash(rgb_img, hash_size=8)
            return str(h), fmt
    except Exception as err:
        if isinstance(err, ValueError):
            raise
        raise ValueError(f"Invalid or corrupted image data: {type(err).__name__}")
