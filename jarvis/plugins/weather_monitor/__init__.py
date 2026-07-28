"""
Weather Monitor Plugin

Provides weather check tools using real-time open APIs.
"""

from typing import Any
import httpx
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter
from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus

# --- Tool ---

class WeatherCheckTool(Tool):
    """Checks the current weather for a specific location using Open-Meteo."""
    
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
        location = kwargs.get("location")
        if not location:
            return "Please provide a location."

        try:
            async with httpx.AsyncClient() as client:
                # 1. Geocode the location
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
                geo_response = await client.get(geo_url)
                geo_response.raise_for_status()
                geo_data = geo_response.json()

                if not geo_data.get("results"):
                    return f"Could not find location: {location}"
                
                lat = geo_data["results"][0]["latitude"]
                lon = geo_data["results"][0]["longitude"]
                city = geo_data["results"][0]["name"]
                
                # 2. Get weather
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
                weather_response = await client.get(weather_url)
                weather_response.raise_for_status()
                weather_data = weather_response.json()
                
                current = weather_data.get("current_weather", {})
                if not current:
                    return f"Weather data not available for {city}."

                temp = current.get("temperature", "N/A")
                windspeed = current.get("windspeed", "N/A")
                weathercode = current.get("weathercode", -1)
                
                if weathercode == 0:
                    cond = "Clear"
                elif 1 <= weathercode <= 3:
                    cond = "Cloudy"
                elif 45 <= weathercode <= 48:
                    cond = "Foggy"
                elif 51 <= weathercode <= 67:
                    cond = "Rainy"
                elif 71 <= weathercode <= 77:
                    cond = "Snowy"
                elif weathercode >= 95:
                    cond = "Stormy"
                else:
                    cond = "Unknown condition"
                
                return f"The current weather in {city} is {cond} and {temp}°C (Wind: {windspeed} km/h)."
        except Exception as e:
            return f"Error fetching weather data for {location}: {e}"

# --- Plugin Entry Point ---

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register tools."""
    # 1. Register tools
    registry.register(WeatherCheckTool())
    
    # Background agent removed as indiscriminate polling of external weather APIs without proper configuration is not recommended.
