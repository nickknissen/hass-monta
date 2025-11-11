"""Constants for the Monta API client."""

import enum

# API Configuration
API_BASE_URL = "https://public-api.monta.com/api/v1/"
DEFAULT_TIMEOUT = 10

# Token refresh settings
PREEMPTIVE_REFRESH_TTL_IN_SECONDS = 300

# Private fields to filter from logs
PRIVATE_INFORMATION = [
    "accessToken",
    "refreshToken",
    "serialNumber",
    "latitude",
    "longitude",
    "address1",
    "address2",
    "address3",
]


class ChargerStatus(enum.StrEnum):
    """Charger Status Description."""

    AVAILABLE = "available"
    BUSY = "busy"
    BUSY_BLOCKED = "busy-blocked"
    BUSY_CHARGING = "busy-charging"
    BUSY_NON_CHARGING = "busy-non-charging"
    BUSY_NON_RELEASED = "busy-non-released"
    BUSY_RESERVED = "busy-reserved"
    BUSY_SCHEDULED = "busy-scheduled"
    ERROR = "error"
    DISCONNECTED = "disconnected"
    PASSIVE = "passive"
    OTHER = "other"


class WalletStatus(enum.StrEnum):
    """Wallet Status Description."""

    COMPLETE = "complete"
    FAILED = "failed"
    PENDING = "pending"
    RESERVED = "reserved"
    NONE = "none"
