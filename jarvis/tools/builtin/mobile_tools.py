import structlog
from typing import Any

from jarvis.server.companion_manager import companion_manager
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

logger = structlog.get_logger(__name__)

class MobileTapTool(Tool):
    """Tool to tap a specific location on the mobile screen."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_tap",
            description="Tap a specific (x, y) coordinate on the connected mobile companion app screen.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="x",
                    type="integer",
                    description="X coordinate to tap.",
                    required=True,
                ),
                ToolParameter(
                    name="y",
                    type="integer",
                    description="Y coordinate to tap.",
                    required=True,
                ),
            ],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        x = params.get("x")
        y = params.get("y")

        if x is None or y is None:
            return ToolResult(success=False, error="Missing x or y coordinate.")

        try:
            result = await companion_manager.send_command_and_wait(
                action="tap",
                params={"x": x, "y": y},
                target_device="mobile",
                timeout=10
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output=f"Successfully tapped at ({x}, {y}).")
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.tap_failed", error=str(e))
            return ToolResult(success=False, error=f"Tap action failed: {str(e)}")


class MobileTypeTool(Tool):
    """Tool to type text on the mobile companion app."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_type",
            description="Type text using the connected mobile companion app. Usually requires a text field to be focused first.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to type.",
                    required=True,
                ),
            ],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        text = params.get("text")
        if not text:
            return ToolResult(success=False, error="No text provided.")

        try:
            result = await companion_manager.send_command_and_wait(
                action="type_text",
                params={"text": text},
                target_device="mobile",
                timeout=15
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output=f"Successfully typed text.")
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.type_failed", error=str(e))
            return ToolResult(success=False, error=f"Type action failed: {str(e)}")


class MobileScrollTool(Tool):
    """Tool to scroll on the mobile companion app screen."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_scroll",
            description="Scroll the screen on the connected mobile companion app.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="direction",
                    type="string",
                    description="Direction to scroll.",
                    required=True,
                    enum=["up", "down", "left", "right"],
                ),
            ],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        direction = params.get("direction")
        if direction not in ["up", "down", "left", "right"]:
            return ToolResult(success=False, error=f"Invalid direction: {direction}")

        try:
            result = await companion_manager.send_command_and_wait(
                action="scroll",
                params={"direction": direction},
                target_device="mobile",
                timeout=10
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output=f"Successfully scrolled {direction}.")
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.scroll_failed", error=str(e))
            return ToolResult(success=False, error=f"Scroll action failed: {str(e)}")


class MobileReadScreenTool(Tool):
    """Tool to read text elements from the mobile companion app screen."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_read_screen",
            description="Read UI elements and text currently visible on the mobile companion app screen.",
            category=ToolCategory.SYSTEM,
            parameters=[],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        try:
            result = await companion_manager.send_command_and_wait(
                action="read_screen",
                params={},
                target_device="mobile",
                timeout=20
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output=result.get("output", "Screen read successfully but no output provided."))
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.read_screen_failed", error=str(e))
            return ToolResult(success=False, error=f"Read screen action failed: {str(e)}")


class MobileLocationTool(Tool):
    """Tool to get the device's current GPS location."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_get_location",
            description="Retrieve the current GPS location from the mobile companion app.",
            category=ToolCategory.SYSTEM,
            parameters=[],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        try:
            result = await companion_manager.send_command_and_wait(
                action="get_location",
                params={},
                target_device="mobile",
                timeout=15
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output=result.get("output", "Location retrieved."))
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.location_failed", error=str(e))
            return ToolResult(success=False, error=f"Location action failed: {str(e)}")


class MobileBatteryTool(Tool):
    """Tool to get the device's current battery level and status."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_get_battery",
            description="Retrieve the battery level and charging status from the mobile companion app.",
            category=ToolCategory.SYSTEM,
            parameters=[],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        try:
            result = await companion_manager.send_command_and_wait(
                action="get_battery",
                params={},
                target_device="mobile",
                timeout=10
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output=result.get("output", "Battery retrieved."))
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.battery_failed", error=str(e))
            return ToolResult(success=False, error=f"Battery action failed: {str(e)}")


class MobileSendSMSTool(Tool):
    """Tool to send an SMS message natively from the phone."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_send_sms",
            description="Send an SMS message natively from the connected mobile companion app.",
            category=ToolCategory.COMMUNICATION,
            parameters=[
                ToolParameter(
                    name="number",
                    type="string",
                    description="The phone number to send the SMS to.",
                    required=True,
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="The content of the text message.",
                    required=True,
                ),
            ],
            dangerous=True,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        number = params.get("number")
        message = params.get("message")
        if not number or not message:
            return ToolResult(success=False, error="Missing number or message.")

        try:
            result = await companion_manager.send_command_and_wait(
                action="send_sms",
                params={"number": number, "message": message},
                target_device="mobile",
                timeout=15
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output=f"Successfully sent SMS to {number}.")
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.sms_failed", error=str(e))
            return ToolResult(success=False, error=f"SMS action failed: {str(e)}")


class MobileMakeCallTool(Tool):
    """Tool to initiate a phone call natively from the phone."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_make_call",
            description="Initiate a phone call natively from the connected mobile companion app.",
            category=ToolCategory.COMMUNICATION,
            parameters=[
                ToolParameter(
                    name="number",
                    type="string",
                    description="The phone number to call.",
                    required=True,
                ),
            ],
            dangerous=True,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        number = params.get("number")
        if not number:
            return ToolResult(success=False, error="Missing number.")

        try:
            result = await companion_manager.send_command_and_wait(
                action="make_call",
                params={"number": number},
                target_device="mobile",
                timeout=15
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output=f"Successfully initiated call to {number}.")
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.call_failed", error=str(e))
            return ToolResult(success=False, error=f"Call action failed: {str(e)}")


class MobileNotificationTool(Tool):
    """Tool to display a push notification on the mobile phone."""

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mobile_show_notification",
            description="Display a native push notification on the mobile companion app.",
            category=ToolCategory.SYSTEM,
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="The title of the notification.",
                    required=True,
                ),
                ToolParameter(
                    name="message",
                    type="string",
                    description="The body text of the notification.",
                    required=True,
                ),
            ],
            dangerous=False,
        )

    async def execute(self, **params: Any) -> ToolResult:
        if not companion_manager.has_companions():
            return ToolResult(success=False, error="No local companions are currently connected.")

        title = params.get("title")
        message = params.get("message")
        if not title or not message:
            return ToolResult(success=False, error="Missing title or message.")

        try:
            result = await companion_manager.send_command_and_wait(
                action="show_notification",
                params={"title": title, "message": message},
                target_device="mobile",
                timeout=10
            )
            if result.get("status") == "success":
                return ToolResult(success=True, output="Successfully showed notification.")
            else:
                return ToolResult(success=False, error=result.get("error", "Unknown error from companion."))
        except Exception as e:
            logger.error("mobile_tools.notification_failed", error=str(e))
            return ToolResult(success=False, error=f"Notification action failed: {str(e)}")


def get_mobile_tools() -> list[Tool]:
    """Return instances of all mobile tools."""
    return [
        MobileTapTool(),
        MobileTypeTool(),
        MobileScrollTool(),
        MobileReadScreenTool(),
        MobileLocationTool(),
        MobileBatteryTool(),
        MobileSendSMSTool(),
        MobileMakeCallTool(),
        MobileNotificationTool(),
    ]
