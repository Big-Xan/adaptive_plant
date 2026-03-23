# 🌱 Adaptive Plant

A fully local, event-driven Home Assistant custom integration for tracking and managing your plants — with intelligent adaptive watering logic that learns your plants' needs over time. Includes a companion Lovelace card with a full visual editor and a task reminder blueprint for Companion App notifications.

![Adaptive Plant Card](https://github.com/user-attachments/assets/1ec6be2a-0d48-43dd-a9f1-b806f7b70404)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![HA Version](https://img.shields.io/badge/HA-2024.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---
## Contents
- [Features](#features)
- [Installation](#installation)
- [Setup](#setup)
- [Entities](#entities)
- [Adaptive Logic](#adaptive-logic)
- [Companion Lovelace Card](#-companion-lovelace-card)
- [Task Reminder Blueprint](#-task-reminder-blueprint)
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
- Configurable reminder notifications if health hasn't been checked recently
- **Confirm Health** button — press to confirm you've checked on your plant without needing to change the health value. Resets the check-in clock.

### 🧪 Fertilization (optional)
- Track fertilization on a separate interval
- Same sensor pattern as watering
- Snoozing watering also snoozes fertilization if it is due the same day

### 💧 Moisture Sensor Integration (optional)
- Link any existing sensor entity
- Automatically reschedule watering if soil is dry
- Automatically mark as watered if soil is saturated
- Adaptive watering logic is disabled for moisture sensor plants — the sensor drives watering decisions, the schedule acts as a fallback only

### 📝 Notes (optional)
- Free-form text field stored per plant

### 🖼️ Plant Image (optional)
- Attach a `/local/` image path to display on dashboard cards. Can be changed via configuration after entry is created. I recommend uploading your plant images to your `/www/` folder.

### 🏠 Area & Label Support
- Assign each plant to a Home Assistant area during setup
- Optionally add a **label** (e.g. `Left shelf`, `Window sill`) to group plants within an area
- Labels can be added, changed, or removed at any time via the integration's settings
- Unlabelled plants always appear first within their area

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
   - Plant name, area, optional label, watering interval, adaptive thresholds
   - Optional features (fertilization, notes, image, moisture sensor)
   - Last watered date (Today / Yesterday / Custom / Haven't yet)
   - Last fertilized date (if enabled)
   - Image path (if enabled)
   - Moisture thresholds (if a sensor was selected)

To edit any setting after setup, go to **Settings → Devices & Services → Adaptive Plant → Configure**.

> **Tip:** To remove a label after setup, open Configure and leave the label field blank, type a space and save, or type the word `null` — all are treated as no label.

---

## Entities

Each plant creates a device with the following entities:

| Entity | Type | Description |
|--------|------|-------------|
| Last watered | Sensor | Date of last watering |
| Next watering | Sensor | Scheduled next watering date |
| Days until watering | Sensor | Human-readable countdown |
| Early watering count | Sensor | Diagnostic — consecutive periods watered early |
| Consecutive periods snoozed | Sensor | Diagnostic — consecutive periods snoozed before watering |
| Health | Select | Excellent / Good / Poor / Sick |
| Watering interval | Number | Editable interval in days |
| Mark watered | Button | Records watering, applies adaptive logic |
| Snooze today's tasks | Button | Delays watering (and fertilization if also due) by 1 day |
| Confirm health | Button | Resets the health check-in clock without changing the health value |
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
If you press **Snooze today's tasks** during a watering period and then water the plant, a snooze streak counter increments. Once it reaches the configured threshold across consecutive periods, the watering interval increases by 1 day (maximum 365). The streak resets if you water without snoozing.

> **Note:** Snoozing and then watering the same plant on the same day will count that period as both early and snoozed. This is a known edge case that will be addressed in a future release.

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

> **Tip:** If you update the card and don't see changes, make sure you've cleared your cache.

### Card Features

- **Today tab** — plants due or overdue, grouped by area and label. Mark watered, mark fertilized, or snooze directly from the card. Hold the button at the bottom to complete all tasks at once. The snooze button remains visible until all of a plant's tasks for the day are resolved.
- **Upcoming tab** — future waterings and fertilizations with a configurable day cutoff. Plants with both tasks due on the same day appear as a single combined row. Mark tasks early directly from the card.
- **Overview tab** — all plants grouped by area and label, with a configurable sort order (alphabetical, health, or days until watering). Expand any plant to see next watering/fertilization dates, edit health, add notes, confirm health check-in, and mark tasks complete.
- **Labels** — plants with a label assigned are grouped under a sublabel header within their area, across all tabs
- **Health ring** — colored ring around each plant avatar indicating health status, configurable per tab
- **Confirm Health button** — always visible in the Overview expanded detail. Shows a heart icon and reads "Update Due" when a health check-in is overdue. Color configurable.
- **Transparent background** — option to hide the card background, compatible with frosted glass themes
- **Pin hold button** — optionally fix the "Hold to complete all" button to the bottom of the card
- **Full visual editor** — configure everything without writing YAML

### Card Configuration & Visual Editor

The card is fully configurable via the visual editor — no YAML required. The card can be modified via YAML if that is your preference (scroll down).

**Default configuration (no options set):**

![Adaptive Plant Card default](https://github.com/user-attachments/assets/197cb184-1b00-4dc0-9916-2c4cfced9315)
```yaml
type: custom:adaptive-plant-card
```

**Using native HA mdi icons, centered in-room labels with color changed to gold, height max set with mark all tasks completed button pinned to the bottom of the card so it's always in the same place.:**

![Adaptive Plant Card with MDI icons](https://github.com/user-attachments/assets/27e1bb06-9ece-4d09-9fa4-999f80cbdd84)
```yaml
type: custom:adaptive-plant-card
label_align: center
label_color: gold
height: 750
pin_hold_button: true
health:
  ring: true
  text: false
  colors:
    Excellent: "#7cb97e"
icons:
  water: mdi:water
  water_color: "#64b4ff"
  fertilize: mdi:flower
  fertilize_color: "#7cb97e"
  snooze: mdi:bell-sleep
  snooze_color: "#aaaaaa"
  fertilize_done: mdi:check
  fertilize_done_color: "#7cb97e"
  water_done: mdi:check
  water_done_color: "#64b4ff"
```

**For full YAML configuration reference:**
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

# Card appearance
show_background: true     # set false for transparent/frosted glass themes
pin_hold_button: false    # set true to fix hold bar to bottom of card

# Overview sort order
overview_sort: alphabetical   # alphabetical | health | watering

# Label appearance
label_align: left         # left | center | right
label_padding: 20         # px offset from the chosen edge
label_color: '#666666'    # optional — defaults to --secondary-text-color

# Area & label header sizing
area_header_size: 12      # optional — font size in px for area name headers
area_header_color: '#888888'  # optional — color for area name headers
label_header_size: 11     # optional — font size in px for label sub-headers
                          # label_header color is set via label_color above

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
  health_confirm: 'mdi:cards-heart'       # icon for Confirm Health button
  health_confirm_color: '#aaaaaa'         # color when check-in is not overdue
  health_confirm_overdue_color: '#e05c5c' # color when check-in is overdue
```

All options are... they're optional — omit any to use defaults.

---

## 📋 Task Reminder Blueprint

A companion blueprint for daily plant task reminders is included in this repo. Sends a single combined notification when any of your plants have watering or fertilization tasks due or overdue — automatically discovering all plants without any manual configuration. Supports up to three daily reminder times, customizable notification text, an optional task count summary (e.g. "4 Waterings and 2 Fertilizations"), and a tap action to open your plant dashboard directly. Plants can be individually excluded from watering or fertilization reminders. Compatible with the Home Assistant Companion App (iOS and Android).

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Big-Xan/adaptive_plant/main/blueprints/automation/adaptive_plant/plant_task_reminders.yaml)

Or manually import via **Settings → Automations & Scenes → Blueprints → Import Blueprint** and paste:
```
https://raw.githubusercontent.com/Big-Xan/adaptive_plant/main/blueprints/automation/adaptive_plant/plant_task_reminders.yaml
```

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
