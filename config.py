"""
Centralized Configuration
=========================
All project settings loaded from .env with sensible defaults.
Import this module instead of reading os.environ directly.
"""

import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

# ---------------------------------------------------------------------------
# Pipeline Settings
# ---------------------------------------------------------------------------
MAGNITUDE_THRESHOLD: float = float(os.getenv("MAGNITUDE_THRESHOLD", "4.5"))

# ---------------------------------------------------------------------------
# MQTT — ShakeAlert
# ---------------------------------------------------------------------------
MQTT_BROKER_URL: str = os.getenv("MQTT_BROKER_URL", "alert.eew.shakealert.org")
MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "8883"))
MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "eew/sys/gm-contour/data")
MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", "")
MQTT_CLIENT_ID: str = os.getenv("MQTT_CLIENT_ID", "alert_worker")
MQTT_TLS_ENABLED: bool = os.getenv("MQTT_TLS_ENABLED", "true").lower() == "true"
MQTT_MESSAGE_TIMEOUT: int = int(os.getenv("MQTT_MESSAGE_TIMEOUT", "600"))  # 10 min

# ---------------------------------------------------------------------------
# AWS / DynamoDB
# ---------------------------------------------------------------------------
AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION: str = os.getenv("AWS_REGION", "us-west-2")
DYNAMODB_TABLE: str = os.getenv("DYNAMODB_TABLE", "ShakeAlert_MQTT_Capture")
CLOUDWATCH_LOG_GROUP: str = os.getenv("CLOUDWATCH_LOG_GROUP", "ShakeAlert_MQTT_Alert")
CLOUDWATCH_LOG_STREAM: str = os.getenv("CLOUDWATCH_LOG_STREAM", "AlertStream")

# ---------------------------------------------------------------------------
# PeopleSense
# ---------------------------------------------------------------------------
PEOPLESENSE_API_URL: str = os.getenv(
    "PEOPLESENSE_API_URL",
    "https://w8bdwhaps0.execute-api.us-west-2.amazonaws.com/v1/occupancy",
)
PEOPLESENSE_API_KEY: str = os.getenv("PEOPLESENSE_API_KEY", "")

# ---------------------------------------------------------------------------
# Gemini LLM
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# HeyGen (stubbed)
# ---------------------------------------------------------------------------
HEYGEN_API_KEY: str = os.getenv("HEYGEN_API_KEY", "")

# ---------------------------------------------------------------------------
# API Server
# ---------------------------------------------------------------------------
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))

# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------
def is_mqtt_enabled() -> bool:
    """MQTT is enabled when broker credentials are configured."""
    return bool(MQTT_USERNAME and MQTT_PASSWORD)

def is_heygen_enabled() -> bool:
    """HeyGen is enabled when API key is provided."""
    return bool(HEYGEN_API_KEY)

def is_aws_configured() -> bool:
    """AWS is configured when access keys are provided."""
    return bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY)
