"""
Jarvis OS - Guardian Fraud Shield

Scans incoming messages and emails for potential scams, phishing, and OTP fraud.
"""

import re
import logging

logger = logging.getLogger(__name__)

class FraudScanner:
    """Scans text for phishing indicators, urgency, and OTP requests."""
    
    URGENCY_KEYWORDS = [
        r"\burgent\b", r"\bimmediately\b", r"\baction required\b", 
        r"\bverify your account\b", r"\bsuspended\b", r"\bblocked\b"
    ]
    
    OTP_KEYWORDS = [
        r"\botp\b", r"\bone time password\b", r"\bverification code\b",
        r"\bsecurity code\b", r"\bdo not share this code\b"
    ]
    
    SUSPICIOUS_LINKS = [
        r"bit\.ly", r"tinyurl\.com", r"t\.co", r"cutt\.ly", r"goo\.gl"
    ]
    
    @classmethod
    def scan(cls, text: str, source: str = "unknown") -> tuple[bool, str]:
        """
        Scans text and returns (is_suspicious, annotated_text).
        """
        if not text:
            return False, text
            
        lower_text = text.lower()
        score = 0
        reasons = []
        
        # Check urgency
        for kw in cls.URGENCY_KEYWORDS:
            if re.search(kw, lower_text):
                score += 1
                reasons.append("High urgency language")
                break
                
        # Check OTP
        for kw in cls.OTP_KEYWORDS:
            if re.search(kw, lower_text):
                score += 2
                reasons.append("OTP / Verification Code request")
                break
                
        # Check links
        for kw in cls.SUSPICIOUS_LINKS:
            if re.search(kw, lower_text):
                score += 1
                reasons.append("Suspicious shortened link")
                break
                
        is_suspicious = score >= 2
        
        if is_suspicious:
            logger.warning(f"Guardian intercepted suspicious {source} message: {', '.join(reasons)}")
            warning_header = f"[GUARDIAN_WARNING: Potential Phishing/Scam detected. Reasons: {', '.join(reasons)}. Do not auto-reply or click links.]\n\n"
            return True, warning_header + text
            
        return False, text
