from typing import Any
from jarvis.plugins.sdk import Plugin, PluginMetadata
from jarvis.events.bus import EventBus
from jarvis.tools.base import Tool
from .tools import WalletTool, SmartContractTool

class Web3WalletPlugin(Plugin):
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="web3_wallet",
            version="1.0.0",
            description="Provides tools for web3 wallet integration."
        )

    async def register(self, bus: EventBus) -> None:
        pass

    def tools(self) -> list[Tool]:
        return [
            WalletTool(),
            SmartContractTool()
        ]
