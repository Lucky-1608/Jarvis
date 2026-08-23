"""
Jarvis OS — Vision API Routes.

POST /api/vision/analyze     — Upload image for analysis
POST /api/vision/screenshot  — Capture and analyze screen
POST /api/vision/find        — Find a UI element on screen
POST /api/vision/errors      — Check screen for errors
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

router = APIRouter()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    query: str = Field(
        "Describe what's in this image.",
        description="Question about the image",
    )


class FindElementRequest(BaseModel):
    description: str = Field(..., description="Description of the UI element to find")


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
@router.post("/vision/analyze", response_model=VisionResponse)
async def analyze_image(
    query: str = "Describe what's in this image.",
    file: UploadFile = File(...),
):
    """Upload an image and analyze it with AI vision."""
    from jarvis.vision.analyzer import VisionAnalyzer

    content = await file.read()
    image_b64 = base64.b64encode(content).decode("utf-8")

    analyzer = VisionAnalyzer()
    result = await analyzer.analyze_screenshot(image_b64, query=query)

    return VisionResponse(**result.to_dict())


@router.post("/vision/screenshot", response_model=VisionResponse)
async def analyze_screen(request: AnalyzeRequest | None = None):
    """Capture the current screen and analyze it."""
    from jarvis.vision.analyzer import VisionAnalyzer

    analyzer = VisionAnalyzer()
    result = await analyzer.read_screen()

    return VisionResponse(**result.to_dict())


@router.post("/vision/find", response_model=VisionResponse)
async def find_element(request: FindElementRequest):
    """Find a specific UI element on screen."""
    from jarvis.vision.analyzer import VisionAnalyzer

    analyzer = VisionAnalyzer()
    result = await analyzer.find_element(request.description)

    return VisionResponse(**result.to_dict())


@router.post("/vision/errors", response_model=VisionResponse)
async def check_errors():
    """Capture screen and check for error messages."""
    from jarvis.vision.analyzer import VisionAnalyzer

    analyzer = VisionAnalyzer()
    result = await analyzer.read_error()

    return VisionResponse(**result.to_dict())


class TrackObjectRequest(BaseModel):
    description: str = Field(..., description="Object to track")


class CompareScenesRequest(BaseModel):
    image1_b64: str | None = None
    image2_b64: str | None = None


@router.post("/vision/track", response_model=VisionResponse)
async def track_object(request: TrackObjectRequest):
    """Start tracking an object across frames (Simulated)."""
    return VisionResponse(
        summary=f"Tracking object: {request.description}",
        elements=[{"name": request.description, "status": "tracking_started"}],
        confidence=0.9
    )


@router.post("/vision/compare", response_model=VisionResponse)
async def compare_scenes(request: CompareScenesRequest):
    """Compare two scenes for differences (Simulated)."""
    return VisionResponse(
        summary="Scene comparison is a simulated feature for now.",
        elements=[],
        confidence=0.5
    )

