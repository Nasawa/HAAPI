# Automations: triggers, conditions and the request action

[← Back to the README](../README.md)

## Triggers

*Requires Home Assistant 2026.7 or later.*

HAAPI provides integration-specific triggers so automations can react the moment a call completes — without pressing a button, adding a `delay`, and then watching the response sensor. Watching `sensor.{endpoint}_response` with a generic state trigger is unreliable, because that sensor's state is the HTTP status code: two calls that both return `200` produce no state change, so the automation never fires. The triggers below fire on the actual call completion instead.

| Trigger | Fires when |
| --- | --- |
| **Response received** | A call completes, for any result. Optional **Status code** field limits it to one status (e.g. `429`). |
| **Call succeeded** | A call completes with a `2xx` status. |
| **Call failed** | A call fails: a network/timeout error (status `0`) or an HTTP error (status `400`+). |
| **Response changed** | The response body differs from the previous call to that endpoint. |
| **Status code changed** | The HTTP status code differs from the previous call to that endpoint. |
| **Response body matches** | The response body matches a regular expression (`pattern`). |
| **Response value matches** | A JSON field (`path`, e.g. `state` or `ams.0.humidity`) `equals` a value or matches a `pattern`. With neither, fires whenever the path resolves. |
| **Response value changed** | A JSON field (`path`) differs from the previous call — field-level version of *Response changed*. |
| **Recovered** | A call succeeds (2xx) after the previous call had failed. |
| **Went down** | A call fails after the previous call had succeeded (2xx). |

Each trigger can target one or more endpoint devices, or be left untargeted to fire for every endpoint.

JSON field paths are dotted (`state`, `ams.0.humidity`), with list items addressed by index. This is a lightweight built-in resolver — no JSONPath dependency. If the body isn't JSON or the path doesn't resolve, value triggers simply don't fire.

**Trigger variables** — every trigger exposes the result under `trigger`:

| Variable | Description |
| --- | --- |
| `trigger.endpoint_name` | The endpoint's name |
| `trigger.endpoint_id` | The endpoint's internal ID |
| `trigger.status` | HTTP status code (`0` = network/timeout error) |
| `trigger.ok` | `true` for a `2xx` status |
| `trigger.body` | Response body (truncated per the endpoint's max response size) |
| `trigger.headers` | Response headers as a dictionary |
| `trigger.truncated` | Whether the body was truncated |
| `trigger.status_changed` | Whether the status changed vs. the previous call |
| `trigger.body_changed` | Whether the body changed vs. the previous call |
| `trigger.previous_status` | The previous call's status code (`null` on the first call) |
| `trigger.previous_body` | The previous call's response body (`null` on the first call) |

**Example** — notify only when an endpoint's response actually changes:
```yaml
automation:
  - alias: "Notify when API result changes"
    trigger:
      - trigger: haapi.response_changed
        target:
          device_id: <your HAAPI endpoint device>
    action:
      - action: notify.mobile_app
        data:
          message: "API changed: {{ trigger.body }}"
```

**Example** — alert on a failed call:
```yaml
automation:
  - alias: "Alert on API failure"
    trigger:
      - trigger: haapi.call_failed
    action:
      - action: notify.mobile_app
        data:
          message: "{{ trigger.endpoint_name }} failed (status {{ trigger.status }})"
```

**Example** — act only when a specific JSON field reaches a value:
```yaml
automation:
  - alias: "Notify when print finishes"
    trigger:
      - trigger: haapi.value_matches
        target:
          device_id: <your HAAPI endpoint device>
        options:
          path: state
          equals: FINISH
    action:
      - action: notify.mobile_app
        data:
          message: "Print finished"
```

## Conditions

*Requires Home Assistant 2026.7 or later.*

HAAPI also provides integration-specific **conditions** so an automation can gate on the result of an endpoint's most recent call without templating. Each condition targets one or more endpoint devices (with multiple, all must satisfy it) and is evaluated live against the stored response.

| Condition | Passes when |
| --- | --- |
| **Last call succeeded** | The endpoint's last call returned a `2xx` status. |
| **Response contains** | The last response body matches a regex (`pattern`). |
| **Response value is** | A JSON field (`path`) `equals` a value or matches a `pattern`. With neither, passes whenever the path resolves. |

**Example** — only act if the last status fetch succeeded:
```yaml
automation:
  - alias: "Refresh only when API is healthy"
    trigger:
      - trigger: time_pattern
        minutes: "/5"
    condition:
      - condition: haapi.last_call_succeeded
        target:
          device_id: <your HAAPI endpoint device>
    action:
      - action: button.press
        target:
          entity_id: button.my_endpoint_trigger
```

## Actions

### `haapi.request`

Calls a single targeted endpoint and **returns its response**, so an automation can use the result in the very next step — no button-press + `wait`/`delay`, and no race. Target a single HAAPI endpoint device.

Returns: `endpoint_id`, `endpoint_name`, `status`, `ok`, `body`, `headers`, `truncated`.

```yaml
automation:
  - alias: "Clear the plate when a finished print is detected"
    trigger:
      - trigger: state
        entity_id: binary_sensor.printer_door
        from: "on"
        to: "off"
    action:
      - action: haapi.request          # fetch fresh status, get the response back
        target:
          device_id: <status endpoint device>
        response_variable: status
      - condition: "{{ (status.body | from_json).awaiting_plate_clear }}"
      - action: haapi.request          # clear-plate endpoint
        target:
          device_id: <clear-plate endpoint device>
```

This is the synchronous counterpart to the endpoint's **Trigger** button: the button is fire-and-forget (great for dashboards), while `haapi.request` awaits the call and hands you the response.

#### Per-call data: `variables` and `body`

`haapi.request` accepts two optional fields. Both apply to **that one call only** — the stored endpoint is never changed, and calls without them (and Trigger button presses) behave exactly as before.

| Field | Type | What it does |
|-------|------|--------------|
| `variables` | mapping | Extra template variables for this call. Each name is available in the endpoint's URL, headers, body and auth templates (e.g. `{{ message }}`), alongside the usual HA state functions. |
| `body` | string | Replaces the endpoint's configured body for this call, sent **as final text**: HAAPI does not render it again (Home Assistant already rendered any templates in the action's `data`). Omit it, or leave it empty, to use the configured body. |

This removes the need to stash per-call values in helpers first (an `input_text` is capped at 255 characters; `variables` has no such limit).

**Recommended: `variables` + a templated endpoint body.** The endpoint's own templates are where per-call values get inserted (and safely JSON-escaped). Endpoint configured with **Content-Type** `application/json` and **Body**:

```jinja
{"text": {{ message | tojson }}, "satellite": {{ satellite | tojson }}, "urgent": {{ urgent | default(false) | tojson }}}
```

Automation:

```yaml
- action: haapi.request
  target:
    entity_id: button.announce_trigger
  data:
    variables:
      message: "{{ trigger.event.data.message }}"
      satellite: "{{ trigger.event.data.satellite }}"
      urgent: true
  response_variable: result
```

**`body` override: a complete, ready-to-send body.** Use it when this one call needs a different payload altogether. Whatever HA hands over is sent as-is — any templates in it were rendered by HA in the automation, and their *output* is never rendered a second time (so text such as `{{ states(...) }}` arriving in a message stays literal):

```yaml
- action: haapi.request
  target:
    entity_id: button.announce_trigger
  data:
    body: '{"text": "Dinner is ready", "urgent": true}'
```

`variables` are not applied to `body` (they only feed the endpoint's templates), so don't write `{{ message }}` in `body` expecting it to come from `variables` — in an automation HA evaluates it first, where `message` is undefined. If you build `body` from automation data in a template, escape it yourself (e.g. `'{"text": {{ trigger.event.data.message | tojson }}}'`); the `variables` pattern above does that for you.

Tips:
- Use `| tojson` when inserting a variable into a JSON body: it adds the quotes and escapes quotes, backslashes, newlines and non-ASCII correctly, so arbitrary text (any length) stays valid JSON. Use `| urlencode` for URL query values.
- Variable *values* are data, not templates: text such as `{{ ... }}` inside a value is sent literally, never rendered. Prefer `variables` + a templated endpoint body for untrusted text (voice transcripts, messages).
- Home Assistant renders templates in an action's `data` before HAAPI sees it, so a `body:` written in an automation is usually already final text. HA may turn a value that looks like a number or boolean into one (e.g. `"123"` → `123`); add `| string` in the endpoint template if you need it quoted. This coercion only affects *templated* values; a static string such as `"123"` written without a template stays a string.
- A `body` given as a mapping/list (e.g. one HA already parsed from JSON), or a bare boolean, is sent re-serialized as JSON (`true`, not `True`).
