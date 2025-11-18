# 🚨 Breaking Change: Module Renamed to `hass_monta`

## Overview

Version 2.0.0 renames the integration module from `monta` to `hass_monta` to prevent conflicts with the external PyPI package this integration depends on.

**⚠️ This requires manual migration. Please follow the steps below.**

---

## What's Changed

- **Domain**: `monta` → `hass_monta`
- **Entity IDs**: `sensor.monta_*` → `sensor.hass_monta_*`
- **Services**: `monta.start_charging` → `hass_monta.start_charging`
- **Services**: `monta.stop_charging` → `hass_monta.stop_charging`

---

## Quick Migration Guide

### 1️⃣ Remove Old Integration
- Go to **Settings** → **Devices & Services**
- Delete the existing **Monta** integration

### 2️⃣ Update via HACS
- **HACS** → **Integrations** → Find **Monta** → **Update**
- Restart Home Assistant

### 3️⃣ Re-add Integration
- **Settings** → **Devices & Services** → **Add Integration** → Search **Monta**
- Re-enter your credentials

### 4️⃣ Update References
Update all automations, scripts, and dashboards:

**Entity IDs:**
```
sensor.monta_charger_state → sensor.hass_monta_charger_state
sensor.monta_wallet_balance → sensor.hass_monta_wallet_balance
```

**Service Calls:**
```
monta.start_charging → hass_monta.start_charging
monta.stop_charging → hass_monta.stop_charging
```

**Logger (if configured):**
```yaml
custom_components.monta → custom_components.hass_monta
```

---

## Why This Change?

This integration depends on the `monta` Python package from PyPI. Having both share the same name caused:
- Logger namespace collisions
- Debugging confusion
- Potential import issues

Renaming to `hass_monta` follows Home Assistant conventions and eliminates these problems.

---

## Full Migration Guide

For detailed instructions, troubleshooting, and rollback procedures, see:
**[MIGRATION_2.0.0.md](https://github.com/nickknissen/hass-monta/blob/main/MIGRATION_2.0.0.md)**

---

## Need Help?

- 📖 [Migration Guide](https://github.com/nickknissen/hass-monta/blob/main/MIGRATION_2.0.0.md)
- 🐛 [Report Issues](https://github.com/nickknissen/hass-monta/issues)
- 💬 [Discussions](https://github.com/nickknissen/hass-monta/discussions)

---

## What to do if something breaks?

If you need to rollback to v1.3.0:
1. Uninstall via HACS
2. Install version 1.3.0 specifically
3. Restart Home Assistant
4. Re-add integration

---

**Full Changelog**: https://github.com/nickknissen/hass-monta/compare/v1.3.0...v2.0.0
