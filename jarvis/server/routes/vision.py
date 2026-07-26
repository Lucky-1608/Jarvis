"""
Jarvis OS — Vision API Routes.

POST /api/vision/analyze     — Upload image for analysis
POST /api/vision/screenshot  — Capture and analyze screen
POST /api/vision/find        — Find a UI element on screen
POST /api/vision/errors      — Check screen for errors
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

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
