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
