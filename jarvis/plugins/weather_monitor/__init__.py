"""
Weather Monitor Plugin

Provides weather check tools and a background agent to monitor severe weather.
"""

from typing import Any
import random
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter
from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus
from jarvis.automation.background_agent import BackgroundAgent

# --- Tool ---

class WeatherCheckTool(Tool):
    """Checks the current weather for a specific location."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_weather",
            description="Get the current weather for a specific location.",
            category=ToolCategory.WEB,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="location",
                    type="string",
                    description="City name, e.g. London, San Francisco"
                )
            ]
        )

    async def execute(self, **kwargs) -> Any:
        location = kwargs.get("location", "Unknown")
        # Mock weather response
        conditions = ["Sunny", "Rainy", "Cloudy", "Stormy"]
        temp = random.randint(5, 35)
        cond = random.choice(conditions)
        return f"The current weather in {location} is {cond} and {temp}°C."


# --- Background Agent ---

class WeatherMonitorAgent(BackgroundAgent):
    """Monitors for severe weather changes periodically."""
    
    async def run_loop(self) -> None:
        # 10% chance of a severe weather alert every check
        if random.random() < 0.1:
            await self.notify_hud(
                title="Severe Weather Alert",
                message="A heavy storm is approaching your default location.",
                level="warning"
            )


# --- Plugin Entry Point ---

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register tools and start background agents."""
    # 1. Register tools
    registry.register(WeatherCheckTool())
    
    # 2. Start background agent (checks every 30 seconds for demo purposes)
    agent = WeatherMonitorAgent(name="weather_monitor", bus=bus, interval_seconds=30)
    agent.start()
