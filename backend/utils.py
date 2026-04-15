"""
utils.py — Image processing utilities for the AI Background Remover App.
Handles validation, preprocessing, and background removal using rembg.
"""

import io
import logging
from PIL import Image
from rembg import remove, new_session

# ──────────────────────────────────────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Pre-load the rembg session once at startup to avoid per-request cold starts.
# Uses the u2net model (downloaded automatically on first run ~170 MB).
logger.info("Initialising rembg session (may download model on first run)…")
_SESSION = new_session("u2net")
logger.info("rembg session ready.")


# ──────────────────────────────────────────────────────────────────────────────
# Validation helpers
# ──────────────────────────────────────────────────────────────────────────────

def validate_file_size(file_bytes: bytes) -> None:
    """Raise ValueError if the file exceeds MAX_FILE_SIZE_BYTES."""
    size = len(file_bytes)
    if size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size {size / (1024*1024):.1f} MB exceeds the "
            f"{MAX_FILE_SIZE_MB} MB limit."
        )


def validate_mime_type(content_type: str) -> None:
    """Raise ValueError if the MIME type is not in the allowed set."""
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Unsupported file type '{content_type}'. "
            f"Allowed types: {', '.join(ALLOWED_MIME_TYPES)}."
        )


def validate_image_bytes(file_bytes: bytes) -> Image.Image:
    """
    Try to open the raw bytes as a PIL Image.
    Raises ValueError if the bytes are not a valid image.
    """
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()                      # Detect tampered / corrupted files
        # Re-open after verify() (verify() exhausts the stream)
        img = Image.open(io.BytesIO(file_bytes))
        return img
    except Exception as exc:
        raise ValueError(f"Cannot decode image data: {exc}") from exc


# ──────────────────────────────────────────────────────────────────────────────
# Core processing
# ──────────────────────────────────────────────────────────────────────────────

def remove_background(file_bytes: bytes) -> bytes:
    """
    Run U2Net background removal on raw image bytes.

    Args:
        file_bytes: Raw bytes of the uploaded image.

    Returns:
        PNG bytes of the processed image with transparent background.

    Raises:
        ValueError: On invalid input.
        RuntimeError: On processing failure.
    """
    # 1. Open & convert to RGBA so rembg always gets a consistent format
    original = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    logger.debug("Input image size: %s, mode: %s", original.size, original.mode)

    # 2. Remove background (uses the pre-loaded global session)
    try:
        processed: Image.Image = remove(original, session=_SESSION)
    except Exception as exc:
        logger.exception("rembg processing failed")
        raise RuntimeError(f"Background removal failed: {exc}") from exc

    # 3. Encode result as PNG (preserves alpha channel)
    output_buffer = io.BytesIO()
    processed.save(output_buffer, format="PNG", optimize=True)
    output_bytes = output_buffer.getvalue()
    logger.debug("Output PNG size: %d bytes", len(output_bytes))
    return output_bytes


def replace_background_color(
    file_bytes: bytes, hex_color: str = "#ffffff"
) -> bytes:
    """
    Remove background then fill the transparent area with a solid colour.

    Args:
        file_bytes: Raw bytes of the uploaded image.
        hex_color:  Hex colour string, e.g. '#ff0000'.

    Returns:
        PNG bytes of the image on the specified background colour.
    """
    # Get transparent PNG
    transparent_bytes = remove_background(file_bytes)
    fg = Image.open(io.BytesIO(transparent_bytes)).convert("RGBA")

    # Parse hex colour
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    # Create solid-colour background and composite
    bg = Image.new("RGBA", fg.size, (r, g, b, 255))
    composite = Image.alpha_composite(bg, fg).convert("RGB")

    output_buffer = io.BytesIO()
    composite.save(output_buffer, format="PNG", optimize=True)
    return output_buffer.getvalue()
