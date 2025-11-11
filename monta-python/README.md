# Monta Python Client

A Python client library for the [Monta EV charging API](https://docs.public-api.monta.com).

## Features

- Async/await support using `aiohttp`
- Automatic token refresh and management
- Pluggable token storage system
- Type hints for all models
- Comprehensive error handling
- Privacy-aware logging (filters sensitive data)

## Installation

```bash
pip install monta
```

## Quick Start

```python
import asyncio
import aiohttp
from monta import MontaApiClient

async def main():
    async with aiohttp.ClientSession() as session:
        client = MontaApiClient(
            client_id="your_client_id",
            client_secret="your_client_secret",
            session=session,
        )

        # Get all charge points
        charge_points = await client.async_get_charge_points()

        for cp_id, charge_point in charge_points.items():
            print(f"Charger: {charge_point.name} ({charge_point.state})")

        # Get wallet information
        wallet = await client.async_get_personal_wallet()
        print(f"Balance: {wallet.balance.amount} {wallet.currency.identifier}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Getting API Credentials

1. Visit the [Monta Portal](https://portal2.monta.app/applications)
2. Create a new application to get your `client_id` and `client_secret`

## Usage Examples

### Get Charge Points

```python
# Get all available charge points
charge_points = await client.async_get_charge_points()

for cp_id, cp in charge_points.items():
    print(f"ID: {cp_id}")
    print(f"Name: {cp.name}")
    print(f"Type: {cp.type}")
    print(f"State: {cp.state}")
    print(f"Last Reading: {cp.last_meter_reading_kwh} kWh")
```

### Get Charges for a Charge Point

```python
# Get recent charges for a specific charge point
charges = await client.async_get_charges(charge_point_id=12345)

for charge in charges:
    print(f"Charge ID: {charge.id}")
    print(f"State: {charge.state}")
    print(f"Started: {charge.started_at}")
    print(f"Stopped: {charge.stopped_at}")
```

### Start and Stop Charging

```python
# Start a charge
response = await client.async_start_charge(charge_point_id=12345)

# Stop a charge
response = await client.async_stop_charge(charge_id=67890)
```

### Get Wallet Information

```python
# Get personal wallet
wallet = await client.async_get_personal_wallet()
print(f"Balance: {wallet.balance.amount} {wallet.currency.identifier}")
print(f"Credit: {wallet.balance.credit}")

# Get wallet transactions
transactions = await client.async_get_wallet_transactions()
for tx in transactions:
    print(f"Transaction {tx.id}: {tx.state} at {tx.created_at}")
```

## Custom Token Storage

By default, the client uses in-memory token storage. For production use, you should implement a persistent storage backend:

```python
from monta import MontaApiClient, TokenStorage

class FileTokenStorage(TokenStorage):
    def __init__(self, file_path: str):
        self.file_path = file_path

    async def load(self) -> dict | None:
        try:
            with open(self.file_path, 'r') as f:
                import json
                return json.load(f)
        except FileNotFoundError:
            return None

    async def save(self, data: dict) -> None:
        import json
        with open(self.file_path, 'w') as f:
            json.dump(data, f)

# Use custom storage
async with aiohttp.ClientSession() as session:
    storage = FileTokenStorage("tokens.json")
    client = MontaApiClient(
        client_id="your_client_id",
        client_secret="your_client_secret",
        session=session,
        token_storage=storage,
    )
```

## Error Handling

The client provides specific exceptions for different error scenarios:

```python
from monta import (
    MontaApiClientError,
    MontaApiClientCommunicationError,
    MontaApiClientAuthenticationError,
)

try:
    charge_points = await client.async_get_charge_points()
except MontaApiClientAuthenticationError:
    print("Authentication failed - check your credentials")
except MontaApiClientCommunicationError:
    print("Network error - check your connection")
except MontaApiClientError as e:
    print(f"API error: {e}")
```

## Models

The library includes comprehensive data models:

- `ChargePoint` - Charging station information
- `Charge` - Individual charging session
- `Wallet` - Personal wallet information
- `Balance` - Wallet balance details
- `Currency` - Currency information
- `WalletTransaction` - Transaction records
- `TokenResponse` - Authentication tokens

## Enums

- `ChargerStatus` - Possible charger states (available, busy, error, etc.)
- `WalletStatus` - Possible wallet transaction states (complete, failed, pending, etc.)

## Development

```bash
# Clone the repository
git clone https://github.com/nickknissen/monta-python.git
cd monta-python

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Run type checker
mypy monta
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

This library is not officially affiliated with Monta. It is an independent implementation of the Monta Public API.

## Links

- [Monta API Documentation](https://docs.public-api.monta.com)
- [Monta Portal](https://portal2.monta.app)
- [Issue Tracker](https://github.com/nickknissen/monta-python/issues)
