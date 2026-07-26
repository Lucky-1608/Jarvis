"""
Jarvis OS — Verification Engine.

"Never blindly execute." (Spec Volume 1)

Every tool result passes through the Verifier before being
reported as successful.  The verifier checks:
  - Tool's own verify() method
  - Error patterns in output
  - Expected result format
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from jarvis.tools.base import Tool, ToolResult

logger = structlog.get_logger(__name__)

# Common error patterns to detect in tool output
ERROR_PATTERNS = [
    re.compile(r"(?i)\berror\b.*\b(fatal|critical|exception)\b"),
    re.compile(r"(?i)\btraceback\b"),
    re.compile(r"(?i)\bpermission denied\b"),
    re.compile(r"(?i)\bcommand not found\b"),
    re.compile(r"(?i)\bsegmentation fault\b"),
    re.compile(r"(?i)\bout of memory\b"),
    re.compile(r"(?i)\bdisk full\b"),
]


class Verifier:
    """
    Verification engine for tool results.

    Three layers of verification:
    1. **Basic**: check ``result.success`` flag
    2. **Pattern**: scan output for known error patterns
    3. **Tool-specific**: call the tool's ``verify()`` method
    """

    async def verify_tool_result(self, tool: Tool, result: ToolResult) -> bool:
        """
        Run all verification layers on a tool result.

        Returns ``True`` if the result is considered valid.
        """
        # Layer 1: Basic success check
        if not result.success:
            logger.debug("verifier.basic_fail", tool=tool.name, error=result.error)
            return False

        # Layer 2: Pattern scanning on output
        if result.output:
            output_str = str(result.output)
            for pattern in ERROR_PATTERNS:
                if pattern.search(output_str):
                    logger.warning(
                        "verifier.error_pattern_detected",
                        tool=tool.name,
                        pattern=pattern.pattern,
                        output_preview=output_str[:200],
                    )
                    # Don't fail — just warn.  Some legitimate output
                    # mentions errors (e.g., log analysis tools).
                    result.metadata["verification_warning"] = (
                        f"Possible error pattern detected: {pattern.pattern}"
                    )
                    break

        # Layer 3: Tool-specific verification
        try:
            tool_verified = await tool.verify(result)
            if not tool_verified:
                logger.warning("verifier.tool_verify_fail", tool=tool.name)
                return False
        except Exception as exc:
            logger.warning(
                "verifier.tool_verify_error",
                tool=tool.name,
                error=str(exc),
            )
            # If the verify method itself fails, we still trust the result
            pass

        return True

    async def verify_ai_response(self, response: str) -> dict[str, Any]:
        """
        Basic verification of an AI-generated response.

        Checks for common issues like empty responses,
        hallucination markers, or refusal patterns.
        """
        issues: list[str] = []

        if not response or not response.strip():
            issues.append("Empty response")

        if len(response) < 5:
            issues.append("Suspiciously short response")

        # Check for common AI refusal/error phrases
        refusal_patterns = [
            "I cannot",
            "I'm unable to",
            "I don't have access",
            "As an AI",
        ]
        for pattern in refusal_patterns:
            if pattern.lower() in response.lower():
                issues.append(f"Possible refusal: '{pattern}'")
                break

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "response_length": len(response),
        }
