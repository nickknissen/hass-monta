"""Constants for monta."""

import enum
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Monta"
DOMAIN = "monta"
VERSION = "0.0.0"
ATTRIBUTION = "Data provided by https://docs.public-api.monta.com"

ATTR_CHARGE_POINTS = "charge_points"
ATTR_WALLET = "wallet"
ATTR_TRANSACTIONS = "transactions"

PREEMPTIVE_REFRESH_TTL_IN_SECONDS = 300
STORAGE_KEY = "monta_auth"
STORAGE_VERSION = 1
STORAGE_ACCESS_EXPIRE_TIME = "access_expire_time"
STORAGE_ACCESS_TOKEN = "access_token"
STORAGE_REFRESH_TOKEN = "refresh_token"
STORAGE_REFRESH_EXPIRE_TIME = "refresh_expire_time"

# Polling and rate-limit related defaults
# Base update cadence for latency-sensitive data (charges)
BASE_UPDATE_INTERVAL_SECONDS = 30
# Maximum backoff interval when rate-limited
MAX_UPDATE_INTERVAL_SECONDS = 300  # 5 minutes
# Charge points refresh: fetched at setup; periodic long refresh
CHARGE_POINTS_REFRESH_INTERVAL_SECONDS = 3600  # 60 minutes
# Wallet and transactions refresh interval
WALLET_REFRESH_INTERVAL_SECONDS = 300  # 5 minutes
# Default fallback for how many charge points' charges to fetch per cycle
DEFAULT_CHARGES_BATCH_SIZE = 4
# Short retry threshold for immediate in-client retry of 429s
SHORT_RETRY_THRESHOLD_SECONDS = 2


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
