<p align="center">
  <img src="assets/wordmark.png" alt="HAAPI" width="360">
</p>

<p align="center">
  <em>A universal REST API integration for Home Assistant — one device per endpoint, with native triggers, conditions, and a synchronous request action.</em>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS Custom"></a>
  <a href="https://github.com/Nasawa/HAAPI/releases"><img src="https://img.shields.io/github/v/release/Nasawa/HAAPI" alt="Latest release"></a>
  <a href="https://github.com/Nasawa/HAAPI/actions/workflows/ci.yml"><img src="https://github.com/Nasawa/HAAPI/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Nasawa/HAAPI" alt="License: MIT"></a>
  <a href="https://ko-fi.com/anigeekapps"><img src="https://img.shields.io/badge/Ko--fi-Support-FF5E5B.svg?logo=ko-fi&logoColor=white" alt="Support on Ko-fi"></a>
</p>

---

HAAPI turns any REST API into a first-class Home Assistant citizen. Each endpoint you configure becomes its own **device** with a trigger button and request/response sensors — and, on Home Assistant 2026.7+, HAAPI adds native **triggers**, **conditions**, and a **`haapi.request` action** so automations can call an API and react to the result without `delay` hacks or state-watching workarounds.

## Features

- **One device = one endpoint** — clean, organized, discoverable in the UI.
- **Full config flow** — no YAML required to add or edit an endpoint.
- **Jinja2 templates** everywhere — URLs, headers, body, and auth credentials all render against live Home Assistant state.
- **Every HTTP method** — GET, POST, PUT, DELETE, PATCH.
- **Multiple auth types** — None, HTTP Basic, Bearer token, or API key.
- **Full response capture** — HTTP status, response body, and response headers stored as entity state and attributes, with configurable max response size and truncation.
- **Resilience controls** — per-endpoint timeout, SSL verification toggle, retry count, and retry delay.
- **Native triggers** (HA 2026.7+) — fire automations on `response received`, `call succeeded`/`failed`, `response`/`status changed`, `recovered`/`went down`, regex body match, and JSON-field value match/change — no button-press-then-wait race.
- **Native conditions** (HA 2026.7+) — gate automations on the last call's result (`succeeded`, body regex, JSON field equals/matches) with no templating.
- **Synchronous action** (HA 2026.7+) — `haapi.request` calls an endpoint and returns its response in the same automation step via `response_variable`.
- **Localized** — English plus community-reviewable Spanish, French, and German translations.

## Installation

### HACS (custom repository)

HAAPI installs today as a HACS **custom repository**:

1. In Home Assistant, open **HACS**.
2. Click the **⋮** menu (top-right) → **Custom repositories**.
3. Add the repository URL `https://github.com/Nasawa/HAAPI` with category **Integration**.
4. Find **HAAPI** in the list and click **Download**.
5. **Restart Home Assistant.**

Then add the integration: **Settings → Devices & Services → Add Integration → HAAPI** (domain: `haapi`).

### Manual

1. Copy `custom_components/haapi/` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant, then add the integration as above.

## Configuration

Adding an endpoint is a two-step config flow:

**Step 1 — Request**
- **Endpoint Name** — a unique label (e.g. `Cat Facts`).
- **URL** — the API URL (supports templates).
- **Method** — GET / POST / PUT / DELETE / PATCH.
- **Headers** — optional, `Key: Value` per line.
- **Body / Content-Type** — for POST/PUT/PATCH.
- **Timeout, Verify SSL, Max Response Size, Retries, Retry Delay** — resilience controls.

**Step 2 — Authentication**
- Choose `none`, `basic`, `bearer`, or `api_key` and fill in the matching credentials.

Each configured endpoint creates one **device** with:
- **Button** `{name} Trigger` — press to fire the call (great on dashboards; fire-and-forget).
- **Sensor** `{name} Request` — state = HTTP method; attributes = the configured request.
- **Sensor** `{name} Response` — state = HTTP status code; attributes = `response_body`, `response_headers`, `truncated`.

## Usage

**Quick start — Cat Facts:** create an endpoint with URL `https://catfact.ninja/fact`, method `GET`, auth `none`. Press its Trigger button, then read the fact from the Response sensor's `response_body` attribute.

**Synchronous call in an automation** — fetch and act in the same step:

```yaml
action:
  - action: haapi.request
    target:
      device_id: <your HAAPI endpoint device>
    response_variable: status
  - condition: "{{ (status.body | from_json).ready }}"
  - action: notify.mobile_app
    data:
      message: "API says ready: {{ status.body }}"
```

**React the moment a call completes** (HA 2026.7+):

```yaml
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

Full trigger/condition/action reference, templating details, input-helper recipes, and testing tools are documented in the [repository docs](https://github.com/Nasawa/HAAPI).

## Contributing

**Pull requests and issues are welcome — HAAPI is a community-open MIT project.** If HAAPI is useful to you, help make it better: file a bug, suggest a feature, improve the docs, or send a fix. You don't need permission to get started.

- **Found a bug or have an idea?** [Open an issue](https://github.com/Nasawa/HAAPI/issues) — clear reports and feature requests are genuinely appreciated.
- **Want to send a change?** Fork the repo, create a branch, and open a PR. Small, focused PRs are easiest to review and merge.
- **Running the tests:** `pip install -r requirements_test.txt` then `python -m pytest -q`. Every PR runs the same checks in CI — pytest, [hassfest](https://developers.home-assistant.io/docs/creating_integration_manifest/), and HACS validation — so you can see exactly what will run before you push.
- **Translations** are especially welcome: the non-English strings are community-reviewable, and native-speaker corrections are exactly the kind of contribution this project wants.

New contributors are welcome regardless of experience level. If something's unclear, open an issue and ask.

## Credits & origin

HAAPI was created by **Christopher** ([@Nasawa](https://github.com/Nasawa)) together with **Claw**, his AI partner — Christopher owning the idea, design, and direction, and Claw doing much of the implementation under that direction. We credit it this way because that's how it was honestly built, not to fence it off.

**HAAPI is open to everyone.** Made here, built for the whole Home Assistant community: it's MIT-licensed, and your issues, ideas, and pull requests are genuinely wanted (see [Contributing](#contributing)). The origin story and the open door are both true at once — knowing who started it takes nothing away from its being yours to use, fork, and improve.

## License

Released under the [MIT License](LICENSE).
