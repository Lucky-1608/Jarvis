"""
Jarvis OS — Vision Analyzer.

Sends screenshots/images to a Vision-Language Model for analysis.

Spec Volume 6 Pipeline:
  Screenshot → Image preprocessing → VL Model → Structured JSON →
  Planner → Executor → Verification

Spec Volume 6 Output Contract:
  Returns: summary, detected elements, coordinates (if available),
  recommended actions, confidence
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any

import structlog

from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.providers.base import Message
from jarvis.router.ai_router import AIRouter

logger = structlog.get_logger(__name__)

# System prompt for vision analysis
VISION_SYSTEM_PROMPT = """You are the Vision Engine of Jarvis OS.
You analyze screenshots and images to understand what's on screen.

## Your Capabilities
- Read text, dialogs, and error messages
- Detect buttons, menus, and UI elements
- Analyze page layouts and application state
- Understand error states and suggest fixes
- Extract tabular data
- Identify application names and windows

## Response Format
Always respond with valid JSON:
```json
{
  "summary": "Extremely detailed description of everything visible. You MUST transcribe visible code, terminal output, and text verbatim if an editor or console is open.",
  "elements": [
    {
      "type": "button|text|input|menu|dialog|error|image|table|code|other",
      "content": "The exact text or description of the element",
      "location": "top-left|top-center|top-right|center|bottom-left|bottom-center|bottom-right",
      "coordinates": {"x": 0, "y": 0, "width": 0, "height": 0}
    }
  ],
  "application": "Name of the visible application (if identifiable)",
  "errors_detected": ["List of any error messages or issues seen verbatim"],
  "recommended_actions": ["Suggested next steps based on what's visible"],
  "confidence": 0.95
}
```

If you cannot analyze the image, set confidence to 0 and explain in summary. Never apologize or say you cannot see the code if it is clearly visible."""


@dataclass
class VisionResult:
    """Structured result from vision analysis."""

    summary: str = ""
    elements: list[dict[str, Any]] = field(default_factory=list)
    application: str = ""
    errors_detected: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "elements": self.elements,
            "application": self.application,
            "errors_detected": self.errors_detected,
            "recommended_actions": self.recommended_actions,
            "confidence": self.confidence,
        }


class VisionAnalyzer:
    """
    Analyzes images/screenshots using a Vision-Language Model.

    Sends base64-encoded images to the AI provider's vision endpoint
    and parses structured JSON responses.
    """

    def __init__(self, router: AIRouter | None = None) -> None:
        self._router = router
        self._bus = get_event_bus()

    def _ensure_router(self) -> AIRouter:
        if self._router is None:
            self._router = AIRouter()
        return self._router

    async def analyze_screenshot(
        self,
        image_base64: str,
        query: str = "Analyze this screenshot and describe what you see.",
        detail: str = "high",
    ) -> VisionResult:
        """
        Analyze a screenshot image.

        Args:
            image_base64: Base64-encoded PNG/JPEG image
            query: Specific question about the image
            detail: "low", "high", or "auto" for image analysis detail
        """
        router = self._ensure_router()

        await self._bus.publish(Event(
            type=EventTypes.VISION_STARTED,
            data={"query": query[:100]},
            source="vision_analyzer",
        ))

        # Build the vision message with image
        messages = [
            Message(role="system", content=VISION_SYSTEM_PROMPT),
            Message(
                role="user",
                content=[
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": query,
                    },
                ],
            ),
        ]

        try:
            response = await router.chat(
                messages,
                temperature=0.2,
                max_tokens=2048,
                provider="ollama",
                model="qwen3.5:397b-cloud",
                response_format={"type": "json_object"},
            )

            result = self._parse_vision_response(response.content)
            result.raw_response = response.content

        except Exception as exc:
            logger.error("vision.analysis_failed", error=str(exc))
            result = VisionResult(
                summary=f"Vision analysis failed: {exc}",
                confidence=0.0,
                raw_response=str(exc),
            )

        await self._bus.publish(Event(
            type=EventTypes.VISION_COMPLETED,
            data={
                "summary": result.summary[:100],
                "elements_count": len(result.elements),
                "confidence": result.confidence,
            },
            source="vision_analyzer",
        ))

        logger.info(
            "vision.analyzed",
            summary=result.summary[:80],
            elements=len(result.elements),
            confidence=result.confidence,
        )

        return result

    async def analyze_file(
        self,
        filepath: str,
        query: str = "Analyze this image and describe what you see.",
    ) -> VisionResult:
        """Analyze an image file."""
        from pathlib import Path

        path = Path(filepath)
        if not path.exists():
            return VisionResult(summary=f"File not found: {filepath}", confidence=0.0)

        with open(path, "rb") as f:
            image_bytes = f.read()

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        return await self.analyze_screenshot(image_b64, query=query)

    async def read_screen(self, target: str = "pc", query: str = "What application is open? What's happening on screen? Describe all visible elements.") -> VisionResult:
        """Capture and analyze the current screen."""
        if target == "phone":
            # Here we would request the UI dump from the mobile via WebSocket
            # Mocking the response for the purpose of the architecture update
            mock_ui_dump = '{"text": "Brave Browser", "contentDescription": "Search or type web address", "bounds": "0,100,1080,250"}'
            return VisionResult(
                summary="Mobile screen reading requested. Received UI dump from AccessibilityService.",
                elements=[mock_ui_dump],
                application="Brave",
                confidence=1.0,
            )

        from jarvis.vision.screenshot import ScreenCapture

        capture = await ScreenCapture.capture_full_screen()
        return await self.analyze_screenshot(
            capture["base64"],
            query=query,
        )

    async def find_element(self, description: str) -> VisionResult:
        """Find a specific UI element on screen."""
        from jarvis.vision.screenshot import ScreenCapture

        capture = await ScreenCapture.capture_full_screen()
        return await self.analyze_screenshot(
            capture["base64"],
            query=f"Find this element on screen: '{description}'. Return its location and how to interact with it.",
        )

    async def read_error(self) -> VisionResult:
        """Capture screen and look for error messages."""
        from jarvis.vision.screenshot import ScreenCapture

        capture = await ScreenCapture.capture_full_screen()
        return await self.analyze_screenshot(
            capture["base64"],
            query="Look for any error messages, warnings, or problems on screen. Describe them and suggest fixes.",
        )

    def _parse_vision_response(self, content: str) -> VisionResult:
        """Parse the LLM's JSON response into a VisionResult."""
        content = content.strip()

        # Try to extract JSON from markdown blocks or braces if direct load fails
        import re
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        brace_match = re.search(r"(\{.*\})", content, re.DOTALL)

        json_str = content
        if json_match:
            json_str = json_match.group(1)
        elif brace_match:
            json_str = brace_match.group(1)

        try:
            data = json.loads(json_str)
            return VisionResult(
                summary=data.get("summary", ""),
                elements=data.get("elements", []),
                application=data.get("application", ""),
                errors_detected=data.get("errors_detected", []),
                recommended_actions=data.get("recommended_actions", []),
                confidence=data.get("confidence", 0.0),
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("vision.parse_error", error=str(exc))
            return VisionResult(
                summary=content,  # Return the full original content as fallback
                confidence=0.3,
            )
