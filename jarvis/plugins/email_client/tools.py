import os
import smtplib
from email.message import EmailMessage
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class EmailSendTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="EmailSendTool",
            description="Send an email.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="to", type="string", description="Recipient email address"),
                ToolParameter(name="subject", type="string", description="Email subject"),
                ToolParameter(name="body", type="string", description="Email body content")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        
        if not smtp_user or not smtp_pass:
            return ToolResult(success=False, error="SMTP_USER and SMTP_PASS environment variables not set.")
            
        try:
            msg = EmailMessage()
            msg.set_content(kwargs.get("body"))
            msg["Subject"] = kwargs.get("subject")
            msg["From"] = smtp_user
            msg["To"] = kwargs.get("to")
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                
            return ToolResult(success=True, output={"message": "Email sent successfully."})
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class EmailReadTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="EmailReadTool",
            description="Stub for reading emails via IMAP.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        if not os.getenv("IMAP_USER"):
            return ToolResult(success=False, error="IMAP_USER environment variable not set.")
        return ToolResult(success=True, output={"message": "IMAP reading requires complex parsing, functionality deferred."})
