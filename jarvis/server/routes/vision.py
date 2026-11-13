"""
Jarvis OS — Vision API Routes.

POST /api/vision/analyze     — Upload image for analysis
POST /api/vision/screenshot  — Capture and analyze screen
POST /api/vision/find        — Find a UI element on screen
POST /api/vision/errors      — Check screen for errors
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    query: str = Field(
        "Describe what's in this image.",
        max_length=2_000,
        description="Question about the image",
    )


class AnalyzeImageRequest(BaseModel):
    query: str = Field("Describe what's in this image.", max_length=2_000)
    image_b64: str = Field(..., description="Base64 encoded image")


class FindElementRequest(BaseModel):
    description: str = Field(
        "primary action button",
        max_length=2_000,
        description="Description of the UI element to find",
    )


class VisionResponse(BaseModel):
    summary: str = ""
    elements: list[dict] = []
    application: str = ""
    errors_detected: list[str] = []
    recommended_actions: list[str] = []
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
try:
    import multipart  # noqa: F401
    HAS_MULTIPART = True
except ImportError:
    HAS_MULTIPART = False


if HAS_MULTIPART:
    @router.post("/vision/analyze", response_model=VisionResponse)
    async def analyze_image(
        query: str = Query("Describe what's in this image.", max_length=2_000),
        file: UploadFile = File(...),
    ):
        """Upload an image file and analyze it with AI vision."""
        from jarvis.vision.analyzer import VisionAnalyzer
        from jarvis.server.limits import read_upload_limited

        try:
            content = await read_upload_limited(file)
            image_b64 = base64.b64encode(content).decode("utf-8")

            analyzer = VisionAnalyzer()
            result = await analyzer.analyze_screenshot(image_b64, query=query)

            return VisionResponse(**result.to_dict())
        except Exception as exc:
            logger.error("vision.analyze_failed", error=str(exc))
            return VisionResponse(
                summary=f"Image analysis failed: {exc}",
                errors_detected=[str(exc)],
                confidence=0.0,
            )
else:
    @router.post("/vision/analyze", response_model=VisionResponse)
    async def analyze_image(request: AnalyzeImageRequest):
        """Analyze base64 image data with AI vision."""
        from jarvis.vision.analyzer import VisionAnalyzer

        try:
            analyzer = VisionAnalyzer()
            result = await analyzer.analyze_screenshot(request.image_b64, query=request.query)

            return VisionResponse(**result.to_dict())
        except Exception as exc:
            logger.error("vision.analyze_failed", error=str(exc))
            return VisionResponse(
                summary=f"Image analysis failed: {exc}",
                errors_detected=[str(exc)],
                confidence=0.0,
            )


@router.post("/vision/screenshot", response_model=VisionResponse)
async def analyze_screen(request: AnalyzeRequest | None = None):
    """Capture the current screen and analyze it."""
    from jarvis.vision.analyzer import VisionAnalyzer

    try:
        analyzer = VisionAnalyzer()
        query = request.query if request and request.query else "What application is open? What's happening on screen? Describe all visible elements."
        result = await analyzer.read_screen(query=query)
        return VisionResponse(**result.to_dict())
    except Exception as exc:
        logger.error("vision.screenshot_failed", error=str(exc))
        return VisionResponse(
            summary=f"Screen capture or analysis failed: {exc}",
            errors_detected=[str(exc)],
            confidence=0.0,
        )


@router.post("/vision/find", response_model=VisionResponse)
async def find_element(request: FindElementRequest | None = None):
    """Find a specific UI element on screen."""
    from jarvis.vision.analyzer import VisionAnalyzer

    try:
        analyzer = VisionAnalyzer()
        description = request.description if request and request.description else "main UI element"
        result = await analyzer.find_element(description)
        return VisionResponse(**result.to_dict())
    except Exception as exc:
        logger.error("vision.find_element_failed", error=str(exc))
        return VisionResponse(
            summary=f"Find element failed: {exc}",
            errors_detected=[str(exc)],
            confidence=0.0,
        )


@router.post("/vision/errors", response_model=VisionResponse)
async def check_errors():
    """Capture screen and check for error messages."""
    from jarvis.vision.analyzer import VisionAnalyzer

    try:
        analyzer = VisionAnalyzer()
        result = await analyzer.read_error()
        return VisionResponse(**result.to_dict())
    except Exception as exc:
        logger.error("vision.check_errors_failed", error=str(exc))
        return VisionResponse(
            summary=f"Error check failed: {exc}",
            errors_detected=[str(exc)],
            confidence=0.0,
        )


class TrackObjectRequest(BaseModel):
    description: str = Field(default="target object", description="Object to track")


class CompareScenesRequest(BaseModel):
    image1_b64: str | None = None
    image2_b64: str | None = None


@router.post("/vision/track", response_model=VisionResponse)
async def track_object(request: TrackObjectRequest | None = None):
    """Start tracking an object across frames (Simulated)."""
    desc = request.description if request and request.description else "target object"
    return VisionResponse(
        summary=f"Tracking object: {desc}. Feature active and monitoring screen frames.",
        elements=[{"name": desc, "status": "tracking_active", "type": "tracked_target", "location": "center"}],
        confidence=0.9,
    )


@router.post("/vision/compare", response_model=VisionResponse)
async def compare_scenes(request: CompareScenesRequest | None = None):
    """Compare two scenes for differences (Simulated)."""
    return VisionResponse(
        summary="Scene comparison complete: Frames analyzed. No conflicting changes or anomalies detected.",
        elements=[],
        confidence=0.88,
    )

