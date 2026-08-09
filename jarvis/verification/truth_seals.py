"""
Jarvis OS - Truth Seals

Forces the AI to generate a verifiable seal of truth (a cryptographic or database record) 
when it claims to have executed a side-effecting action.
"""

import time
import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

class TruthSealManager:
    """Manages the creation and verification of Truth Seals for tool execution."""
    
    _seals = {}

    @classmethod
    def issue_seal(cls, tool_name: str, parameters: dict, result: Any) -> str:
        """
        Issues a Truth Seal for a successful side-effecting tool call.
        """
        timestamp = time.time()
        
        # Serialize deterministically
        data_str = json.dumps({
            "tool": tool_name,
            "params": parameters,
            "result": str(result),
            "timestamp": timestamp
        }, sort_keys=True)
        
        # Create a SHA-256 hash as the seal ID
        seal_id = "seal_" + hashlib.sha256(data_str.encode()).hexdigest()[:16]
        
        cls._seals[seal_id] = {
            "tool": tool_name,
            "timestamp": timestamp,
            "valid": True
        }
        
        logger.info(f"Issued Truth Seal [{seal_id}] for {tool_name}")
        return seal_id
        
    @classmethod
    def verify_seal(cls, seal_id: str) -> bool:
        """Verifies if a Truth Seal exists and is valid."""
        return cls._seals.get(seal_id, {}).get("valid", False)
