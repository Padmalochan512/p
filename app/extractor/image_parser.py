from PIL import Image
from pathlib import Path
import io
import base64

def process_image_file(file_path: Path) -> dict:
    """
    Validates and processes image files, converts to RGB, and generates base64 / bytes.
    """
    with Image.open(file_path) as img:
        rgb_img = img.convert("RGB")
        width, height = rgb_img.size
        
        buf = io.BytesIO()
        rgb_img.save(buf, format="JPEG", quality=90)
        jpeg_bytes = buf.getvalue()
        base64_str = base64.b64encode(jpeg_bytes).decode("utf-8")
        
        return {
            "width": width,
            "height": height,
            "format": img.format or "JPEG",
            "bytes": jpeg_bytes,
            "base64": base64_str
        }
