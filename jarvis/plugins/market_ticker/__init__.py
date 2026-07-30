import httpx
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult
from jarvis.tools.registry import ToolRegistry
from jarvis.events.bus import EventBus

class GetCryptoPriceTool(Tool):
    """Fetches real-time crypto prices."""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="get_crypto_price",
            description="Get the current price of a cryptocurrency in USD.",
            category=ToolCategory.WEB,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="coin_id",
                    type="string",
                    description="The CoinGecko ID of the cryptocurrency (e.g., 'bitcoin', 'ethereum', 'dogecoin')."
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        coin_id = kwargs.get("coin_id", "").lower()
        if not coin_id:
            return ToolResult(success=False, error="No coin_id provided.")

        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                if coin_id not in data:
                    return ToolResult(success=False, error=f"Could not find price data for '{coin_id}'. Ensure you are using the correct CoinGecko ID.")
                    
                price = data[coin_id].get("usd")
                return ToolResult(success=True, output=f"The current price of {coin_id.capitalize()} is ${price:,.2f} USD.")
        except Exception as e:
            return ToolResult(success=False, error=f"Error fetching crypto price: {str(e)}")

def setup(registry: ToolRegistry, bus: EventBus) -> None:
    """Register the market ticker tools."""
    registry.register(GetCryptoPriceTool())
