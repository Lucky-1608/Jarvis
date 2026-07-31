import os
from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

class CloudProvisionTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="CloudProvisionTool",
            description="Provision or manage AWS EC2 instances.",
            category=ToolCategory.SYSTEM,
            dangerous=True,
            parameters=[
                ToolParameter(name="action", type="string", description="list, start, or stop"),
                ToolParameter(name="instance_id", type="string", description="EC2 instance ID (for start/stop).")
            ]
        )
        
    async def execute(self, **kwargs) -> ToolResult:
        if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
            return ToolResult(success=False, error="AWS credentials are not set in environment variables.")
            
        action = kwargs.get("action")
        instance_id = kwargs.get("instance_id")
        
        try:
            import boto3
            ec2 = boto3.client('ec2', region_name=os.getenv("AWS_REGION", "us-east-1"))
            
            if action == "list":
                res = ec2.describe_instances()
                instances = []
                for resrv in res.get("Reservations", []):
                    for inst in resrv.get("Instances", []):
                        instances.append({"id": inst["InstanceId"], "state": inst["State"]["Name"]})
                return ToolResult(success=True, output={"instances": instances})
            elif action == "start" and instance_id:
                ec2.start_instances(InstanceIds=[instance_id])
                return ToolResult(success=True, output={"message": f"Started {instance_id}"})
            elif action == "stop" and instance_id:
                ec2.stop_instances(InstanceIds=[instance_id])
                return ToolResult(success=True, output={"message": f"Stopped {instance_id}"})
            else:
                return ToolResult(success=False, error="Invalid action or missing instance_id.")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
