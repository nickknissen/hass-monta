# Monta

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

_Integration to integrate with [monta][monta]._

**This integration sets up the following:**

Platform | Entities
-- | --
`binary_sensor` | Cable Plugged In
`sensor` | Charge point Visibility, Type, State, Last meter reading (kWh), Last Charge (with attributes), Personal Wallet amount, Latest Wallet Transactions
`switch` | Charger Start/Stop
`services` | `start_charging` and `stop_charging`

## Installation


### HACS installation (recommended)  

1. Download the integration via HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nickknissen&repository=hass-monta&category=integration)
2. Click download
3. Restart Home Assistant
4. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Monta"

### HACS installation (custom repository)
1. Go to HACS in Home Assistant
2. Click on integrations
3. In top right corner, click three dots, click 'Custom repositories'
4. Paste this repository URL (https://github.com/nickknissen/hass-monta/) in repository box
5. Choose integration in category box
6. Click add, wait while repository is added, close window
7. Click the new repository, and click download
8. Restart Home Assistant
9. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Monta"



### Manual installation
1. Using your tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `monta`.
1. Download _all_ of the files from the `custom_components/monta/` directory [here](https://github.com/nickknissen/hass-monta/tree/main/custom_components/monta), in this repository.
1. Place the files you downloaded into the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations", click "+", and search for "Monta"

## Configuration is done in the UI
👉 Monta Public API is in BETA currently.
In order to obtain client id/Client secret to it, you might have to opt-in to their Beta program. This can be done in your user account settings in the app or in Monta's CPMS.

Client id and secret are obtained from https://portal2.monta.app/applications.

<!---->

## Rate limiting and update cadence
- The integration respects Monta Public API rate limits and HTTP 429 responses.
- On 429, it reads `context.rateLimitResponse.resetsIn` from the response JSON body and backs off accordingly. It does not rely on `Retry-After` or other rate-limit headers.
- To reduce bursts:
  - Charge points are fetched at setup and cached, then refreshed infrequently (default every 60 minutes).
  - Wallet and transactions refresh every 5 minutes by default.
  - Charges (latency-sensitive) refresh every 30 seconds, staggered across multiple charge points to stay well under quota.
- When backing off due to a 429, you will see an INFO log and the coordinator temporarily increases its update interval (capped at 5 minutes) and then recovers automatically.

## Entities and services

- Charge point sensors
  - Visibility: `public` or `private`
  - Type: `ac` or `dc`
  - State: charger state (enum)
  - Last meter reading: cumulative energy (kWh)
  - Last Charge: exposes latest charge state; attributes include timestamps like `startedAt`, `stoppedAt`, etc.
- Wallet sensors
  - Personal Wallet amount (with `credit` attribute when available)
  - Latest Wallet Transactions: attributes include a parsed list of recent transactions
- Binary sensors
  - Cable Plugged In
- Switches
  - Start/Stop charging
- Services
  - `monta.start_charging` and `monta.stop_charging`
    - Both accept a `charge_point_id` (select your charger device in the UI Service call dialog to populate it)

## Development

- Quick test: `scripts/develop` launches HA with this integration and local `config/`.
- Setup tooling: `scripts/setup` installs Python deps (HA, Ruff, etc.).
- Lint: `scripts/lint` runs Ruff checks and autofixes style.
- In HA UI, add the Monta integration and supply Client ID/Secret.
- Validate that entities appear and update; watch logs for any rate-limit backoff messages.

## Troubleshooting

- 429 Too Many Requests
  - The integration automatically backs off based on Monta’s `resetsIn` hint and resumes normal cadence afterward.
  - You may see: `Rate limited by API. Backing off update interval to …` in logs.
- Authentication
  - If credentials are invalid or tokens expire, HA will surface a config entry auth error; reconfigure the integration.
- Privacy
  - Access/refresh tokens are stored using HA’s Storage (`.storage/`) and sensitive fields are redacted from logs.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[monta]: https://docs.public-api.monta.com
[commits-shield]: https://img.shields.io/github/commit-activity/y/nickknissen/hass-monta.svg?style=for-the-badge
[commits]: https://github.com/nickknissen/hass-monta/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/nickknissen/hass-monta.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Nick%20Nissen%20%40nickknissen-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/nickknissen/hass-monta.svg?style=for-the-badge
[releases]: https://github.com/nickknissen/hass-monta/releases
