# Troubleshooting

[← Back to the README](../README.md)

## Troubleshooting

### Check Logs

Enable debug logging in `configuration.yaml`:

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

