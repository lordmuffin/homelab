# Grill-Stats Development Secrets

This directory contains the 1Password integration for grill-stats development environment secrets.

## 1Password Setup Required

Create a new item in your 1Password HomeLab vault with the following details:

**Item Name:** `grill-stats-dev-creds-1password`  
**Item Type:** `Secure Note` or `Login`

### Required Fields

Add the following fields to your 1Password item:

| Field Name | Type | Description | Example Value |
|------------|------|-------------|---------------|
| `thermoworks-client-id` | Text | ThermoWorks OAuth Client ID | `tw_client_dev_123` |
| `thermoworks-client-secret` | Password | ThermoWorks OAuth Client Secret | `tw_secret_dev_abc123...` |
| `homeassistant-token` | Password | Home Assistant Long-Lived Access Token | `eyJ0eXAiOiJKV1QiLCJhbGc...` |
| `db-username` | Text | PostgreSQL Database Username | `grill_monitor_dev` |
| `db-password` | Password | PostgreSQL Database Password | `dev_secure_password_123` |
| `redis-password` | Password | Redis Authentication Password | `redis_dev_password_456` |
| `secret-key` | Password | Flask Secret Key (min 32 chars) | `dev_flask_secret_key_minimum_32_characters` |
| `influxdb-token` | Password | InfluxDB Access Token | `influx_dev_token_xyz789...` |

## Files in this Directory

- `grill-stats-dev-creds-1password.yaml` - 1Password OnePasswordItem resource
- `README.md` - This documentation file

## Related Files

- `../patches/grill-stats-env-patch.yaml` - Environment variables for main Flask app
- `../patches/device-service-env-patch.yaml` - Environment variables for device service
- `../patches/temperature-service-env-patch.yaml` - Environment variables for temperature service

## Migration Benefits

This refactoring provides:

✅ **Centralized Secret Management**: All secrets in one 1Password item  
✅ **No Plain Text Secrets**: No more .env files in git  
✅ **Automatic Rotation**: Secrets update when 1Password item changes  
✅ **Audit Trail**: 1Password tracks all secret access  
✅ **Team Sharing**: Easy to share access via 1Password vaults  

## Usage

Once the 1Password item is created and populated:

1. ArgoCD will detect the changes
2. 1Password Connect Operator will sync the secrets
3. Pods will automatically use the new secret values

No manual kubectl commands needed - it's all GitOps! 🚀