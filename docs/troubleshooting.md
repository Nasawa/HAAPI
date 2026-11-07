# Troubleshooting

[← Back to the README](../README.md)

## Troubleshooting

### Check Logs

Turn on debug logging from the UI, no restart needed:

1. Go to **Settings → Devices & services** and open **HAAPI**
2. Open the three-dot menu and select **Enable debug logging**
3. Reproduce the problem
4. Open the same menu and select **Disable debug logging**. Home Assistant downloads the log file, ready to attach to a bug report.

To keep debug logging on across restarts, add this to `configuration.yaml` instead:

```yaml
logger:
  default: info
  logs:
    custom_components.haapi: debug
```

### Common Issues

1. **Templates not rendering**: Ensure your template syntax is correct
2. **Authentication failing**: Verify credentials and auth type
3. **Connection errors**: Check URL accessibility from your HA instance

