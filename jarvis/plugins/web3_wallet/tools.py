import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class WalletTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="WalletTool",
            description="Check Ethereum wallet balance.",
            category=ToolCategory.SYSTEM,
            dangerous=False,
            parameters=[
                ToolParameter(name="address", type="string", description="Wallet address")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        rpc_url = os.getenv("ETH_RPC_URL")
        if not rpc_url:
            return ToolResult(success=False, error="ETH_RPC_URL environment variable required.")
            
        address = kwargs.get("address")
        try:
            import requests
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [address, "latest"],
                "id": 1
            }
            res = requests.post(rpc_url, json=payload)
            if res.status_code == 200:
                balance_hex = res.json().get("result")
                balance_eth = int(balance_hex, 16) / 10**18
                return ToolResult(success=True, output={"address": address, "balance_eth": balance_eth})
            return ToolResult(success=False, error=res.text)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class SmartContractTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(name="SmartContractTool", description="Smart Contract execution stub.", category=ToolCategory.SYSTEM, dangerous=True, parameters=[])
    async def execute(self, **kwargs) -> ToolResult: return ToolResult(success=True, output={"message": "Smart Contract ABI execution deferred."})
