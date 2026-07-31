import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class StripeMetricsTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="StripeMetricsTool",
            description="Get recent Stripe charges.",
            category=ToolCategory.SYSTEM,
            dangerous=False,
            parameters=[
                ToolParameter(name="limit", type="integer", description="Number of charges to fetch")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        api_key = os.getenv("STRIPE_API_KEY")
        if not api_key:
            return ToolResult(success=False, error="STRIPE_API_KEY environment variable not set.")
            
        limit = kwargs.get("limit", 5)
        try:
            import stripe
            stripe.api_key = api_key
            charges = stripe.Charge.list(limit=limit)
            data = [{"amount": c.amount, "currency": c.currency, "status": c.status} for c in charges.data]
            return ToolResult(success=True, output={"charges": data})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
