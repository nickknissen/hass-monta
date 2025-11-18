# Migration Guide: v2.0.0

## Breaking Changes

Version 2.0.0 renames the Python module from `monta` to `hass_monta` to avoid conflicts with the external PyPI package that this integration depends on.

**This is a breaking change that requires manual migration.**

---

## What Changed

- **Integration Domain**: `monta` → `hass_monta`
- **Entity IDs**: All entities will have new IDs (e.g., `sensor.monta_charger_state` → `sensor.hass_monta_charger_state`)
- **Service Calls**: `monta.start_charging` → `hass_monta.start_charging`, `monta.stop_charging` → `hass_monta.stop_charging`
- **Storage**: Integration will use a new storage key
- **Logger**: `custom_components.monta` → `custom_components.hass_monta`

---

## Why This Change?

This integration depends on an external Python package called `monta` (from PyPI). Having both the integration and the package share the same name can cause:
- Logger namespace collisions
- Confusion during debugging
- Potential import resolution issues

Renaming to `hass_monta` follows Home Assistant naming conventions and eliminates these conflicts.

---

## Migration Steps

### Step 1: Export Current Configuration (Optional but Recommended)

Before upgrading, note down:
- Your client ID and client secret (you'll need to re-enter these)
- Any automations, scripts, or dashboards that reference Monta entities or services
- Any custom scan interval settings you configured

### Step 2: Remove Old Integration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Find the **Monta** integration
3. Click the three dots (⋮) and select **Delete**
4. Confirm deletion

### Step 3: Update the Integration

**If using HACS:**
1. Go to **HACS** → **Integrations**
2. Find **Monta** in your installed integrations
3. Click **Update** (or **Redownload** if update doesn't appear)
4. Restart Home Assistant

**If using manual installation:**
1. Delete the old `custom_components/monta/` directory
2. Download the latest release (v2.0.0)
3. Extract to `custom_components/hass_monta/`
4. Restart Home Assistant

### Step 4: Re-add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **Monta**
4. Enter your client ID and client secret
5. Configure scan intervals (if you had custom settings)

### Step 5: Update Entity References

All entities will have new IDs. You'll need to update:

#### Automations
**Before:**
```yaml
trigger:
  - platform: state
    entity_id: sensor.monta_charger_power
```

**After:**
```yaml
trigger:
  - platform: state
    entity_id: sensor.hass_monta_charger_power
```

#### Scripts
**Before:**
```yaml
service: monta.start_charging
data:
  charge_point_id: 12345
```

**After:**
```yaml
service: hass_monta.start_charging
data:
  charge_point_id: 12345
```

#### Dashboard Cards
**Before:**
```yaml
type: entities
entities:
  - sensor.monta_charger_state
  - sensor.monta_wallet_balance
```

**After:**
```yaml
type: entities
entities:
  - sensor.hass_monta_charger_state
  - sensor.hass_monta_wallet_balance
```

### Step 6: Update Logger Configuration (If Applicable)

If you have custom logger configuration in `configuration.yaml`:

**Before:**
```yaml
logger:
  logs:
    custom_components.monta: debug
```

**After:**
```yaml
logger:
  logs:
    custom_components.hass_monta: debug
```

### Step 7: Verify Everything Works

1. Check that all your devices and entities are discovered
2. Test any automations that use Monta entities or services
3. Verify dashboard cards are displaying correctly
4. Test the `hass_monta.start_charging` and `hass_monta.stop_charging` services

---

## Finding and Replacing Entity IDs

To find all references to old entity IDs in your Home Assistant configuration:

1. Go to **Developer Tools** → **States**
2. Search for entities starting with `hass_monta_` (these are your new entities)
3. Note the entity IDs you're using

To find automations/scripts using old entities:
1. Go to **Settings** → **Automations & Scenes**
2. Check each automation for `monta` references
3. Update entity IDs and service calls as needed

---

## Common Issues

### Issue: Integration doesn't appear after update
**Solution**: Clear your browser cache and hard refresh (Ctrl+F5 / Cmd+Shift+R)

### Issue: Old entities still appear
**Solution**: The old entities will remain until you delete the old integration. Follow Step 2 to remove them.

### Issue: Can't find the integration to re-add
**Solution**: Make sure you've restarted Home Assistant after updating the integration files.

### Issue: Automations stopped working
**Solution**: Check that you've updated both entity IDs (`sensor.monta_*` → `sensor.hass_monta_*`) and service calls (`monta.*` → `hass_monta.*`)

---

## Rollback Instructions

If you encounter issues and need to rollback:

1. In HACS, uninstall the Monta integration
2. Add custom repository: `https://github.com/nickknissen/hass-monta`
3. Install version 1.3.0
4. Restart Home Assistant
5. Re-add the integration with domain `monta`

---

## Need Help?

If you encounter issues during migration:
- Check the [GitHub Issues](https://github.com/nickknissen/hass-monta/issues)
- Create a new issue with details about your problem
- Include your Home Assistant version and installation method (HACS/manual)

---

## Technical Details

For developers and advanced users:

- The integration module namespace changed from `custom_components.monta` to `custom_components.hass_monta`
- The domain identifier changed from `"monta"` to `"hass_monta"`
- Imports from the external `monta` PyPI package (v1.0.3) remain unchanged
- Entity unique IDs are preserved where possible, but entity IDs will change due to domain change
- Storage key changed from `monta_auth` to maintain compatibility
