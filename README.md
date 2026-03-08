# 🌱 Adaptive Plant

A fully local, event-driven Home Assistant custom integration for tracking and managing your plants — with intelligent adaptive watering logic that learns your plants' needs over time. Includes a companion Lovelace card with a full visual editor.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![HA Version](https://img.shields.io/badge/HA-2024.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Features

### 🚿 Adaptive Watering
- Track watering intervals per plant
- **Adaptive & customizable interval reduction** — if you consistently water early, the interval automatically shortens
- **Adaptive & customizable interval extension** — if you consistently snooze watering, the interval automatically lengthens
- Snooze watering by one day without resetting the period
- Sensors show human-readable status: `Today`, `In 3 Days`, `2 Days Overdue`

### 🌿 Plant Health
- Health select entity: `Excellent`, `Good`, `Poor`, `Sick`
- Configurable reminder notifications if health hasn't been updated recently

### 🧪 Fertilization (optional)
- Track fertilization on a separate interval
- Same sensor pattern as watering

### 💧 Moisture Sensor Integration (optional)
- Link any existing sensor entity
- Automatically reschedule watering if soil is dry
- Automatically mark as watered if soil is saturated

### 📝 Notes (optional)
- Free-form text field stored per plant

### 🖼️ Plant Image (optional)
- Attach a `/local/` image path to display on dashboard cards. Can be changed via configuration after entry is created. I recommend uploading your plant images to your `/www/` folder.

### 🏠 Area Support
- Assign each plant to a Home Assistant area during setup

---

## Installation

### Via HACS (recommended)
1. In HACS, go to **Integrations → Custom Repositories**
2. Add `https://github.com/Big-Xan/adaptive_plant` as an **Integration**
3. Search for **Adaptive Plant** and install
4. Restart Home Assistant

### Manual
1. Copy the `custom_components/adaptive_plant/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Adaptive Plant**
3. Follow the setup wizard:
   - Plant name, area, watering interval, adaptive thresholds
   - Optional features (fertilization, notes, image, moisture sensor)
   - Last watered date (Today / Yesterday / Custom / Haven't yet)
   - Last fertilized date (if enabled)
   - Image path (if enabled)
   - Moisture thresholds (if a sensor was selected)

---

## Entities

Each plant creates a device with the following entities:

| Entity | Type | Description |
|--------|------|-------------|
| Last watered | Sensor | Date of last watering |
| Next watering | Sensor | Scheduled next watering date |
| Days until watering | Sensor | Human-readable countdown |
| Health | Select | Excellent / Good / Poor / Sick |
| Watering interval | Number | Editable interval in days |
| Mark watered | Button | Records watering, applies adaptive logic |
| Snooze watering | Button | Delays watering by 1 day |
| Last fertilized | Sensor | *(if fertilization enabled)* |
| Next fertilization | Sensor | *(if fertilization enabled)* |
| Days until fertilization | Sensor | *(if fertilization enabled)* |
| Fertilization interval | Number | *(if fertilization enabled)* |
| Mark fertilized | Button | *(if fertilization enabled)* |
| Notes | Text | *(if notes enabled)* |

---

## Adaptive Logic

### Watering interval reduction
If you press **Mark Watered** before the scheduled date, an early watering counter increments. Once it reaches the configured threshold, the watering interval is reduced by 1 day (minimum 1). The counter resets if you water on time.

### Watering interval extension
If you press **Snooze Watering** during a watering period and then water the plant, a snooze streak counter increments. Once it reaches the configured threshold across consecutive periods, the watering interval increases by 1 day (maximum 365). The streak resets if you water without snoozing.

---

## 🃏 Companion Lovelace Card

This repo includes a companion Lovelace card (`adaptive-plant-card.js`) with a full visual editor, designed specifically for use with this integration.

### Card Installation

1. Copy `www/adaptive-plant-card.js` to your HA `config/www/` directory
2. Go to **Settings → Dashboards → Resources → Add Resource**
   - URL: `/local/adaptive-plant-card.js`
   - Type: **JavaScript module**
3. Hard refresh your browser (Ctrl+Shift+R / Cmd+Shift+R)
4. Add a new card and search for **Adaptive Plant Card**

### Card Features

- **Today tab** — plants due or overdue, grouped by area. Mark watered, mark fertilized, or snooze directly from the card. Hold the button at the bottom to complete all tasks at once.
- **Upcoming tab** — future waterings and fertilizations with a configurable day cutoff. Mark tasks early directly from the card.
- **Overview tab** — all plants grouped by area. Expand any plant to see next watering/fertilization dates, edit health, add notes, and mark tasks complete.
- **Health ring** — colored ring around each plant avatar indicating health status, configurable per tab
- **Full visual editor** — configure everything without writing YAML

### Card Configuration

The card is fully configurable via the visual editor. For YAML configuration:

```yaml
type: custom:adaptive-plant-card
# Layout
height: 500               # optional — enables internal scroll
width: 400                # optional

# Tabs
show_today: true
show_upcoming: true
show_overview: true

# Schedule
upcoming_days: 14         # how many days ahead to show (default: 30)
overdue_color: '#e05c5c'  # color for overdue chips and indicators

# Health ring & text
health:
  ring: true              # show health ring globally (default: true)
  text: false             # show health text globally (default: false, overview only)
  ring_width: 3           # ring thickness in px
  ring_today: true        # per-tab override (true / false, omit for global default)
  ring_upcoming: true
  ring_overview: true
  text_overview: true     # text shown on overview by default
  colors:
    Excellent: '#7cb97e'
    Good: '#a8cc8a'
    Poor: '#e6a817'
    Sick: '#e05c5c'

# Icons — use any emoji or MDI icon (e.g. mdi:water)
icons:
  water: '💧'
  water_color: '#64b4ff'
  fertilize: '🌸'
  fertilize_color: '#7cb97e'
  snooze: '🔔'
  snooze_color: '#aaaaaa'
  fertilize_done: '✅'
  fertilize_done_color: '#7cb97e'
  water_done: '✔'
  water_done_color: '#64b4ff'
```

All options are optional — omit any to use defaults.

---

## Privacy & Security

- Fully local — no external API calls, no telemetry, no analytics
- All state stored in config entries only
- No HTTP endpoints registered
- No shell commands executed

---

## Requirements

- Home Assistant 2024.6 or newer
- No additional Python packages required

---

## License

MIT License — see [LICENSE](LICENSE) for details.
