"""
Alert Store
============
Persistence layer for ShakeAlert earthquake alerts.
Supports DynamoDB (production) and local JSON file (development fallback).
"""

import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from decimal import Decimal

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    DYNAMODB_TABLE,
    CLOUDWATCH_LOG_GROUP,
    CLOUDWATCH_LOG_STREAM,
    is_aws_configured,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DynamoDB Alert Store
# ---------------------------------------------------------------------------
class DynamoDBAlertStore:
    """
    Stores alerts in the ShakeAlert_MQTT_Capture DynamoDB table.
    Schema matches the reference script.
    """

    def __init__(self):
        import boto3
        from botocore.exceptions import ClientError

        self._ClientError = ClientError

        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        self._dynamodb = session.resource("dynamodb")
        self._table = self._dynamodb.Table(DYNAMODB_TABLE)
        self._logs_client = session.client("logs")
        self._sequence_token: Optional[str] = None

        # Ensure CloudWatch log group/stream exist
        self._init_cloudwatch()

    def _init_cloudwatch(self):
        """Ensure log group and stream exist."""
        try:
            self._logs_client.create_log_group(logGroupName=CLOUDWATCH_LOG_GROUP)
        except self._logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        except Exception as e:
            logger.warning("CloudWatch log group setup: %s", e)

        try:
            self._logs_client.create_log_stream(
                logGroupName=CLOUDWATCH_LOG_GROUP,
                logStreamName=CLOUDWATCH_LOG_STREAM,
            )
        except self._logs_client.exceptions.ResourceAlreadyExistsException:
            pass
        except Exception as e:
            logger.warning("CloudWatch log stream setup: %s", e)

    def _log_to_cloudwatch(self, message: str):
        """Send a log entry to CloudWatch Logs."""
        try:
            kwargs = {
                "logGroupName": CLOUDWATCH_LOG_GROUP,
                "logStreamName": CLOUDWATCH_LOG_STREAM,
                "logEvents": [
                    {"timestamp": int(time.time() * 1000), "message": str(message)}
                ],
            }
            if self._sequence_token:
                kwargs["sequenceToken"] = self._sequence_token
            response = self._logs_client.put_log_events(**kwargs)
            self._sequence_token = response.get("nextSequenceToken")
        except Exception as e:
            logger.debug("CloudWatch log failed: %s", e)

    def save_alert(
        self, topic: str, raw_xml: str, fields: Dict[str, Any]
    ) -> None:
        """Store an alert in DynamoDB."""
        try:
            item = {
                "OrigTime": fields["orig_time"],
                "Version": str(fields.get("version", "0")),
                "Topic": topic,
                "Magnitude": str(fields.get("magnitude", "")),
                "Latitude": str(fields.get("latitude", "")),
                "Longitude": str(fields.get("longitude", "")),
                "Depth": str(fields.get("depth", "")),
                "Message": raw_xml,
            }
            self._table.put_item(Item=item)
            msg = (
                f"[STORE] Stored Version {fields.get('version')} "
                f"for OrigTime {fields['orig_time']}"
            )
            logger.info(msg)
            self._log_to_cloudwatch(msg)
        except Exception as e:
            logger.error("DynamoDB put_item failed: %s", e)
            self._log_to_cloudwatch(f"[DynamoDB Error] {e}")

    def get_alert(self, orig_time: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single alert by OrigTime."""
        try:
            response = self._table.get_item(Key={"OrigTime": orig_time})
            item = response.get("Item")
            return self._deserialize(item) if item else None
        except Exception as e:
            logger.error("DynamoDB get_item failed: %s", e)
            return None

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent alerts (scan — acceptable for small tables)."""
        try:
            response = self._table.scan(Limit=limit)
            items = response.get("Items", [])
            # Sort by OrigTime descending
            items.sort(key=lambda x: x.get("OrigTime", ""), reverse=True)
            return [self._deserialize(item) for item in items[:limit]]
        except Exception as e:
            logger.error("DynamoDB scan failed: %s", e)
            return []

    @staticmethod
    def _deserialize(item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB Decimal types to Python floats."""
        result = {}
        for key, value in item.items():
            if isinstance(value, Decimal):
                result[key] = float(value)
            else:
                result[key] = value
        return result


# ---------------------------------------------------------------------------
# Local JSON Alert Store (development fallback)
# ---------------------------------------------------------------------------
class LocalAlertStore:
    """
    Stores alerts in a local JSON file for development when AWS is not configured.
    """

    def __init__(self, file_path: str = "data/alerts.json"):
        self._file_path = Path(file_path)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("[]", encoding="utf-8")

    def _read_all(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self._file_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_all(self, alerts: List[Dict[str, Any]]) -> None:
        self._file_path.write_text(
            json.dumps(alerts, indent=2, default=str), encoding="utf-8"
        )

    def save_alert(
        self, topic: str, raw_xml: str, fields: Dict[str, Any]
    ) -> None:
        alerts = self._read_all()
        alerts.append(
            {
                "OrigTime": fields["orig_time"],
                "Version": str(fields.get("version", "0")),
                "Topic": topic,
                "Magnitude": str(fields.get("magnitude", "")),
                "Latitude": str(fields.get("latitude", "")),
                "Longitude": str(fields.get("longitude", "")),
                "Depth": str(fields.get("depth", "")),
                "Timestamp": time.time(),
            }
        )
        self._write_all(alerts)
        logger.info(
            "[LOCAL STORE] Saved alert for OrigTime %s", fields["orig_time"]
        )

    def get_alert(self, orig_time: str) -> Optional[Dict[str, Any]]:
        for alert in self._read_all():
            if alert.get("OrigTime") == orig_time:
                return alert
        return None

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        alerts = self._read_all()
        alerts.sort(key=lambda x: x.get("OrigTime", ""), reverse=True)
        return alerts[:limit]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_alert_store():
    """Create the appropriate alert store based on configuration."""
    if is_aws_configured():
        logger.info("Using DynamoDB alert store (table: %s)", DYNAMODB_TABLE)
        return DynamoDBAlertStore()
    else:
        logger.info("AWS not configured — using local JSON alert store.")
        return LocalAlertStore()
