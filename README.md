# Monta

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

_Integration to integrate with [monta][monta]._

**This integration will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show something `True` or `False`.
`sensor` | Show info from Monta API.
`switch` | Switch something `True` or `False`.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `monta`.
1. Download _all_ the files from the `custom_components/monta/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Monta"

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[monta]: https://github.com/nickknissen/hass-monta
[commits-shield]: https://img.shields.io/github/commit-activity/y/nickknissen/hass-monta.svg?style=for-the-badge
[commits]: https://github.com/nickknissen/hass-monta/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/nickknissen/hass-monta.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Nick%20Nissen%20%40nickknissen-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/nickknissen/hass-monta.svg?style=for-the-badge
[releases]: https://github.com/nickknissen/hass-monta/releases
