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

# Separate scan intervals for different data types
CONF_SCAN_INTERVAL_CHARGE_POINTS = "scan_interval_charge_points"
CONF_SCAN_INTERVAL_WALLET = "scan_interval_wallet"
CONF_SCAN_INTERVAL_TRANSACTIONS = "scan_interval_transactions"

# Delay between the per-charge-point detail requests in a single update cycle.
# Monta's public API allows ~10 requests/min. A full charge-point update makes
# 1 list call + 1 detail call per charge point, so for several chargers the
# requests must be spread out to stay under the limit and avoid HTTP 429.
# 8s => ~7.5 req/min, leaving headroom for the wallet/transaction coordinators.
CONF_CHARGE_POINT_REQUEST_DELAY = "charge_point_request_delay"

DEFAULT_SCAN_INTERVAL_CHARGE_POINTS = 120  # Charge points need frequent updates
DEFAULT_SCAN_INTERVAL_WALLET = 600  # Wallet updates less frequently (10 minutes)
DEFAULT_SCAN_INTERVAL_TRANSACTIONS = (
    600  # Transactions update less frequently (10 minutes)
)
DEFAULT_CHARGE_POINT_REQUEST_DELAY = 8  # seconds between per-charger detail calls

PREEMPTIVE_REFRESH_TTL_IN_SECONDS = 300
STORAGE_KEY = "monta_auth"
STORAGE_VERSION = 1
STORAGE_ACCESS_EXPIRE_TIME = "access_expire_time"
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
