# <img src="https://raw.githubusercontent.com/Big-Xan/adaptive_plant/main/custom_components/adaptive_plant/brand/icon.png" width="32" height="32" style="vertical-align:middle"> Adaptive Plant

A fully local, event-driven Home Assistant custom integration for tracking and managing your plants — with intelligent adaptive watering logic that learns your plants' needs over time. Includes a highly customizable companion Lovelace card with a full visual editor and a task reminder blueprint for Companion App notifications.

<img width="2400" height="1260" alt="Adaptive Plant on a tablet and a phone" src="https://github.com/user-attachments/assets/ecf3ffb3-d45f-454e-9214-cee3669e389e" />

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![HA Version](https://img.shields.io/badge/HA-2024.7%2B-blue)
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
- [Templates & Scripts](#-templates--scripts)
- [Frequently Asked Questions](#-faq)
---

## Features

### 🚿 Adaptive Watering
- Track watering intervals per plant
- **Adaptive & customizable interval reduction** — if you consistently water early, the interval automatically shortens
- **Adaptive & customizable interval extension** — if you consistently snooze watering, the interval automatically lengthens
- Snooze watering without resetting the period: a task due today moves to tomorrow, and an overdue task also moves to tomorrow (not one day past its old due date)
- Sensors show human-readable status: `Today`, `In 3 Days`, `2 Days Overdue`
- **Changing an interval reschedules immediately** — editing a watering or fertilization interval (via the number entity or Configure) recomputes the next due date on the spot: last done + new interval, but never earlier than today. Shortening an interval can make a task due today; it never makes it overdue. Moisture-sensor plants keep their watering date sensor-managed; fertilization reschedules for every plant.

### 🌿 Plant Health
- Health select entity: `Excellent`, `Good`, `Poor`, `Sick`
- Configurable reminder notifications if health hasn't been checked recently
- **Confirm Health** button — press to confirm you've checked on your plant without needing to change the health value. Resets the check-in clock.

### 🧪 Fertilization (optional)
- Track fertilization on a separate interval
- Same sensor pattern as watering
- Snoozing watering also snoozes fertilization if it is due the same day
- **Sync to watering day (optional)** — set a sync window of `1`–`6` days and marking a plant watered will snap an upcoming fertilization that falls within that window onto the same day, so you water and fertilize in one go. Off by default (`0`, fully independent intervals). It never delays a fertilization that's already due or overdue, and is skipped for plants with moisture-sensors enabled. Set it under **Fertilization settings** (at setup or via Configure) — keep it below your watering interval.
- Can be enabled on any plant after setup via Configure — you'll be prompted for the last fertilized date when first enabled. The plant reloads automatically to create the fertilization entities; no manual reload needed.
- The first schedule uses the fertilization interval you entered in the setup wizard (or 30 days if you never set one). To change it, open Configure again — the Fertilization interval field appears once fertilization is active. Changing the interval takes effect immediately: the next fertilization is rescheduled from the last fertilized date.

### 💧 Moisture Sensor Integration (optional)
- Link any existing sensor entity
- Automatically reschedule watering to today when the reading is **at or below** the dry threshold
- Automatically mark as watered when the reading **crosses above** the wet threshold (a rise from at-or-below the threshold). Soil that simply stays wet doesn't re-mark the plant every day.
- If the plant is due but the soil is still moist, the watering moves to tomorrow (at most once a day), so it doesn't sit overdue while the soil is wet. A date that's still in the future is left alone, so the countdown keeps running.
- Adaptive watering logic is disabled for moisture sensor plants — the sensor drives watering decisions, the schedule acts as a fallback only
- Moisture sensor, dry threshold, and wet threshold can all be added, changed, or removed after setup via Configure. Use the Enable moisture sensor toggle to remove a sensor — toggling off clears the sensor and both thresholds.
- The live moisture % can be shown as a chip on any card tab — Overview, Today, and Upcoming — instead of the watering-days countdown (see `show_moisture_in_overview` / `show_moisture_in_today` / `show_moisture_in_upcoming` in the card config below).

> **Note:** On moisture-sensor plants, **Last watered** can be a watering the sensor *detected* (a wet-threshold crossing) rather than a button press — any rise across the wet threshold counts, even a small one (e.g. 69% → 71% with a 70% threshold).

> **Tip:** To remove a moisture sensor after setup, open Configure, toggle Enable moisture sensor off, and save. (The moisture sensor uses Home Assistant's entity picker, which can't be cleared by deleting the value — the toggle is the supported way to remove it.)

### 🪴 Repotting (optional)
- Track when a plant was last repotted via the **Last repotted** date sensor
- **Mark repotted** button stamps today's date as the last repotting event
- **Repotted on** text field — enter a date in `YYYY-MM-DD` format (e.g. `2026-04-01`) before pressing Mark repotted to record a past date instead of today. The field clears automatically after the button is pressed.
- Can be enabled on any plant after setup via Configure — you'll be prompted for the last repotted date when first enabled

> **Note:** The **Repotted on** field accepts dates in `YYYY-MM-DD` format only (e.g. `2026-04-01`). Leave it blank to record today. An invalid date, or a date in the future, shows an error instead of being recorded — nothing is stamped and what you typed stays in the field so you can fix it.

### 🖼️ Plant Image (optional)
Give a plant a photo to display on dashboard cards. There are two ways to do it — pick whichever you prefer, in the setup wizard or later via Configure:

- **Upload a photo (recommended)** — choose a **PNG or JPEG** file directly in the wizard or options flow. The image is processed for you automatically (orientation corrected, downscaled to a max of 1024px, saved as JPEG) and stored privately in `config/adaptive_plant/images/`. Home Assistant never serves that folder publicly: the photo reaches your dashboards through the plant's **Photo** image entity, which only signed-in users can load. Uploaded images are managed by the integration: the old file is cleaned up automatically when you replace the photo, disable the image option, or remove the plant.
- **Enter a `/local/` path** — point at an image you've placed yourself. Note that Home Assistant serves everything in `/www/` (as `/local/`) to anyone who can reach your instance, without signing in; upload the photo instead if that matters to you. I recommend creating a folder titled 'adaptive_plant' in your `/www/` folder and putting your plant images there.
> **Example image pathway (w/ folder created) for card config:**  `/local/adaptive_plant/monstera.png`

> **Example image pathway (without folder, uploaded directly into `/www/`) for card config:**  `/local/monstera.png`

If you supply both an upload and a path at the same time, the **upload wins**.

- In Configure, a changed path must start with `/local/`. Your current photo is kept until you save — closing the dialog without saving leaves the old image in place.

- Image **size** (px) and **shape** (circle / square, softly rounded) are configurable on the companion card via the visual editor or YAML. Set `image_size: 0` to hide plant photos entirely for clean text-only rows.

> **📱 Uploading from an iPhone?** Photos you've taken are HEIC/HEIF, but iOS transcodes them to JPEG when you pick one through the file selector — so iPhone uploads work. A raw `.heic` file (e.g. dragged from a desktop) isn't supported and is rejected with an "invalid image" error.

> **⬆️ Upgrading from v1.2.4 or earlier?** Earlier versions saved uploaded photos in `config/www/adaptive_plant/`, where they could be loaded without signing in. On the first start after upgrading, each plant's uploaded photo is moved to private storage automatically; your plants and dashboards keep showing it. The old `/local/adaptive_plant/…jpg` address stops working, so if you used it anywhere else, switch to the plant's **Photo** entity. Uploaded files that no plant uses (for example from a setup wizard you closed) are never deleted automatically: if any are left in `config/www/adaptive_plant/`, **Settings → Repairs** lists them and lets you delete them, or keep them and hide the notice. Downgrading afterwards hides uploaded photos until you upload them again.

> **🏷️ A note on file names:** Uploaded images get auto-generated names — a 32-character hex string ending in `.jpg` — and those are the *only* files the integration ever deletes on its own. Hand-placed images are left completely untouched, **unless** you happen to give one a 32-character hex name ending in `.jpg` inside `/local/adaptive_plant/`, which would look like a managed file: the setup wizard and Configure won't accept that as a typed path, and one saved before v1.2.5 is moved into private storage like an upload. Any normal name (`monstera.png`, `my_fern.jpg`) is perfectly safe.

### 🔬 Latin Name (optional)
- Store the scientific name for each plant
- Enabled or disabled per plant during setup or via Configure at any time
- Displayed on the companion card below the plant name (if enabled)

### 📝 Notes (optional)
- Free-form text field stored per plant - directly editable via the companion card.
- Up to 255 characters (Home Assistant's limit for an entity state)
- Can be enabled or disabled at any time via Configure — no restart required

### 📖 Care Instructions (optional)
- Free-form care notes per plant — light, soil, humidity, feeding quirks, whatever you want to remember
- Displayed **read-only** on the companion card, in the expanded detail on the Overview tab
- Basic formatting supported: wrap text in `**double asterisks**` for **bold**, and line breaks are preserved
- Up to 2000 characters
- Enabled per plant via Configure at any time. After enabling, **save and reopen Configure** to type your notes (the text box appears once the feature is active). Your text is preserved if you toggle the feature off and back on.

> **Note:** Care instructions are read-only on the card by design — they're a reference you set in Configure, not an editable field on the dashboard. Clearing the text while the feature stays enabled simply hides the Care section.

### 📡 Linked Sensors (optional)
Show readings from any sensor you already have — temperature, humidity, light, soil fertility — right on the plant's row in the companion card.

- Add them under **Configure → Linked sensors → Add a sensor** (or switch on *Linked sensors* in Plant settings). Up to 10 per plant.
- Each sensor appears as a chip on the plant's Overview row and as a row in its expanded detail, updating live. The row is labeled with the sensor's own name without its device's name in front (e.g. *Humidity* rather than *Bedroom Thermometer Humidity*); long names are shortened with an ellipsis so the reading stays on one line.
- Choose an icon (any MDI icon or emoji; defaults to the sensor's own icon), an optional hex color, whether the chip sits **before** or **after** the watering / fertilization chips, and its order.
- **Manage linked sensors** lets you edit, reorder, or remove each one.
- Linked sensors are display-only — they don't affect watering logic (that's what the moisture sensor is for).

> **Note:** A linked sensor is stored by its entity ID. If you rename that entity's ID later, the chip shows `—`; link the sensor again under Configure.

<p align="center">
  <img width="400" alt="Linked sensors on the Overview tab" src="https://github.com/user-attachments/assets/34405f25-2d62-44be-9db9-1985938c4571" />
  <img width="400" alt="Link a sensor dialog" src="https://github.com/user-attachments/assets/290c42fa-58fc-4036-b0f5-82899a456e10" />
</p>

### 🗓️ Seasonal Schedules (Experimental)
Give a plant a different watering (and fertilization) schedule for parts of the year — water less in winter, more in summer, or pause feeding while the plant is dormant.

- Turn on **Seasonal watering schedule** in the setup wizard or in Plant settings. The plant's current intervals become its **base schedule**, which applies to any day/period that falls outside of seasons.
- Add up to 8 seasons. Each has a name (optional), a start and end date (both included), and its own intervals. Seasons can run across New Year (e.g. November 1 – March 14), but can't overlap.
- A new season starts **from** the base schedule or another season, plus or minus a number of days for watering and fertilization. Once saved, each season keeps its own numbers.
- **Pause fertilization** during a season: nothing comes due inside it, and fertilization comes due on the first day after it that isn't paused. Fertilization can't be paused for the whole year.
- The base schedule and every season **learn separately**: early waterings and snoozes adjust whichever period is in effect.
- Changes in the season manager are kept only when you choose **Save seasons**; **Discard changes** leaves the plant as it was.
- The season in effect today shows as the `active_season` attribute on the plant's **Next watering** sensor.
- Turning seasons off (Plant settings) asks which schedule to keep, then deletes the base schedule and all seasons.

> **Experimental:** please report anything odd on the [issue tracker](https://github.com/Big-Xan/adaptive_plant/issues).

<p align="center">
  <img width="370" alt="Seasonal schedule manager" src="https://github.com/user-attachments/assets/8a0fe78c-ec0c-46e9-b423-4f0fba3cad27" />
  <img width="430" alt="Editing the Summer and Winter seasons" src="https://github.com/user-attachments/assets/3e67b689-bc35-48cc-a19c-d2b585a6c5a0" />
</p>

### 🏠 Area & Label Support
- Assign each plant to a Home Assistant area during setup
- The area can be changed — or cleared — at any time after setup from the plant's edit device page (pencil icon on integration page).
- Optionally add a **label** (e.g. `Left shelf`, `Window sill`) to group plants within an area
- Labels can be added, changed, or removed at any time via the integration's settings
- Unlabelled plants always appear first within their area on the companion card.

### 🌱 Duplicate a Plant
Do you also propagate your plants? When you already have **at least one plant already set up**, adding a new one opens a small menu: create a plant from scratch, or **duplicate an existing plant**.

- Duplicating copies the plant's care *recipe*: watering interval (the current, adapted value), adaptive thresholds, enabled features, fertilization settings, seasonal schedule, latin name, care instructions, area, and label
- The lived history starts fresh: health resets to Good with a new check-in clock, adaptive counters at zero, notes empty
- In each "last watered / fertilized / repotted" date step you can pick **Mirror parent plant** to carry the parent's dates over verbatim instead of entering your own
- A moisture sensor and its thresholds are **never copied** — two plants shouldn't share one probe. Link a sensor on the duplicate afterwards via Configure.
- Linked sensors aren't copied either; add them to the duplicate under Configure.
- An *uploaded* photo **isn't** shared between plants — the duplicate keeps the image feature enabled so you can upload its own. A hand-placed `/local/` path **is** copied as-is; shared files are safe and never touched by cleanup.
- Duplicates land in the parent's *current* area (as shown on its device page).

---

## Installation

### Via Marketplace (Home Assistant 2026.11 and later, recommended)
Since Home Assistant 2026.11, HACS is built in as the **Marketplace**.
1. Go to **Settings → Marketplace** (the first time, accept the notice about community projects)
2. Select **Add from link** and enter `https://github.com/Big-Xan/adaptive_plant`
3. Open **Adaptive Plant** and select **Install**
4. Set up your first plant when prompted. If you aren't prompted, go to **Settings → Devices & Services → Add Integration** and search for **Adaptive Plant**. If Home Assistant asks for a restart, restart first.
5. The companion card and task reminder blueprint are registered automatically — no further steps needed.

> Once Adaptive Plant is listed in the default catalog, skip step 2: just search for **Adaptive Plant** in the Marketplace.

### Via HACS (before Home Assistant 2026.11)
1. In HACS, open the menu (⋮) → **Custom repositories**
2. Add `https://github.com/Big-Xan/adaptive_plant` with the type **Integration**
3. Still in HACS, search for **Adaptive Plant** and **Download** it
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration**, search for **Adaptive Plant**, and add your first plant
6. The companion card and task reminder blueprint are registered automatically — no further steps needed.

### Manual
1. Copy the `custom_components/adaptive_plant/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Adaptive Plant**
3. If you already have plants set up, a menu appears first: **Add a plant** (full wizard) or **Duplicate an existing plant** (see [Duplicate a Plant](#-duplicate-a-plant))
4. Follow the setup wizard:
   - Plant name, area, optional label, watering interval, adaptive thresholds
   - Optional features (fertilization, notes, latin name, image, repotting, seasonal schedule, moisture sensor)
   - Last watered date (Today / Yesterday / Custom / Haven't yet — plus Mirror parent plant when duplicating)
   - Last fertilized date (same options) *(if fertilization enabled)*
   - Last repotted date (same options) *(if repotting enabled)*
   - Latin name *(if latin name enabled)*
   - Image — upload a photo or enter a `/local/` path *(if image enabled)*
   - Moisture thresholds *(if a sensor was selected)*
   - Seasons *(if seasonal schedule enabled)*

To edit any setting after setup, go to **Settings → Devices & Services → Adaptive Plant → Configure**. Once a plant has linked sensors or seasons, Configure opens a small menu: **Plant settings**, **Linked sensors**, and **Seasonal schedule**.

<p align="center">
  <img width="440" alt="Configure menu" src="https://github.com/user-attachments/assets/e6553047-c6f1-4e7d-8afa-c0bb6ac175cc" />
</p>

Turning on fertilization, notes, latin name, repotting, or a moisture sensor after setup reloads the plant automatically so its new entities appear — no manual reload or restart.

> **Tip**: To remove a label, latin name, or image after setup, open Configure, clear the field (or, for an uploaded image, disable the image option), and save.

---

## Entities

Each plant creates a device with the following entities:

| Entity | Type | Description |
|--------|------|-------------|
| Last watered | Sensor | Date of last watering |
| Next watering | Sensor | Scheduled next watering date (`active_season` attribute shows the season in effect, if any) |
| Days until watering | Sensor | Human-readable countdown |
| Early watering count | Sensor | Diagnostic — consecutive periods watered early |
| Consecutive periods snoozed | Sensor | Diagnostic — consecutive periods snoozed before watering |
| Health | Select | Excellent / Good / Poor / Sick |
| Watering interval | Number | Editable interval in days |
| Mark watered | Button | Records watering, applies adaptive logic |
| Snooze today's tasks | Button | Moves a due or overdue watering (and fertilization, if also due) to tomorrow |
| Confirm health | Button | Resets the health check-in clock without changing the health value |
| Last fertilized | Sensor | *(if fertilization enabled)* |
| Next fertilization | Sensor | *(if fertilization enabled)* |
| Days until fertilization | Sensor | *(if fertilization enabled)* |
| Fertilization interval | Number | *(if fertilization enabled)* |
| Mark fertilized | Button | *(if fertilization enabled)* |
| Last repotted | Sensor | *(if repotting enabled)* |
| Mark repotted | Button | *(if repotting enabled)* Stamps today's date, or the date in the Repotted on field if set (invalid or future dates show an error) |
| Repotted on | Text | *(if repotting enabled)* Enter a past date (or today) in `YYYY-MM-DD` format before pressing Mark repotted |
| Notes | Text | *(if notes enabled)* Up to 255 characters |
| Latin name | Text | *(if latin name enabled)* |
| Photo | Image | *(if image enabled)* The plant's photo, served only to signed-in users; the Next watering sensor shows it as its picture |
| Soil moisture | Sensor | Diagnostic — live reading from the moisture sensor *(only for plants with a moisture sensor; plants that already had this entity keep it)* |

---

## Adaptive Logic

### Watering interval reduction
If you press **Mark Watered** before the scheduled date, an early watering counter increments. Once it reaches the configured threshold, the watering interval is reduced by 1 day (minimum 1). The counter resets if you water on time.
> **Example:** If you notice a plant that has a 7 day watering interval is dry prior to its set watering date (7th day since last watering) → you water it early repeatedly (marking the watering each time) → once it hits the threshold you entered on set-up the watering period is decreased by a day.

### Watering interval extension
If you press **Snooze today's tasks** when a watering is due, a snooze streak counter increments and the task is pushed to tomorrow. Once it the snooze count reaches the configured threshold across consecutive periods, the watering interval increases by 1 day (maximum 365). The streak resets if you water without snoozing.
> **Example:** If you notice a plant that has a 7 day watering interval is not in need of watering on its due date → you snooze the task until the soil is adequately dry → if this pattern repeats across enough consecutive watering periods to hit the configured threshold, the watering interval is extended by a day to better match the plant's actual needs.

With a seasonal schedule, this learning applies to whichever period (base schedule or season) is in effect on the day you water or snooze.

> **Note:** Snoozing and then watering the same plant on the same day will count that period as both early and snoozed. This is a known edge case and _may_ be addressed in a future release. In the meantime.... don't do that? Why would you do that?

---

## 🃏 Companion Lovelace Card

This repo includes a companion Lovelace card (`adaptive-plant-card.js`) with a full visual editor, designed specifically for use with this integration.

### Card Installation

The card is bundled with the integration and registered automatically as a Lovelace resource when the integration loads — no manual installation required. The integration registers a single HTTP endpoint to serve the card file, which is what enables this automatic registration.

Hard refresh your browser (Ctrl+Shift+R / Cmd+Shift+R) after installing or updating. If the old card still shows (common in the Companion App), clear the frontend cache: in the Companion App use **Reset frontend cache** in the app's settings; in a browser, clear the site data for your Home Assistant address.

> **Upgrading from v1.1.0 or earlier?** Previous versions required manually copying `www/adaptive-plant-card.js` to your HA `config/www/` directory and adding it as a resource under **Settings → Dashboards → Resources**. Remove that old resource entry to avoid the card loading twice.

### Card Features

- **Today tab** — plants due or overdue, grouped by area and label, in the same order as the Overview. Mark watered, mark fertilized, or snooze directly from the card — presses respond instantly, and a finished task turns into a check right where it was instead of the list jumping around. Hold the button at the bottom to complete all tasks at once (or hide that button). The snooze button remains visible until all of a plant's tasks for the day are resolved.
- **Completed Today** *(optional)* — plants you've finished for the day are listed under the active tasks with display-only checks. When nothing's left to do, the tab says **All caught up!** (as a large message if nothing was completed today either).
- **Upcoming tab** — future waterings and fertilizations with a configurable day cutoff. Plants with both tasks due on the same day appear as a single combined row. Mark tasks early directly from the card.
- **Overview tab** — all plants grouped by area and label, with a configurable sort order (alphabetical, health, or days until watering). Expand any plant to see next watering/fertilization dates, edit health, add notes, confirm health check-in, and mark tasks complete.
- **Labels** — plants with a label assigned are grouped under a sublabel header within their area, across all tabs
- **Health ring** — colored ring around each plant avatar indicating health status, configurable per tab
- **Overview task icons** — instead of a generic dot, an Overview row shows a red water, fertilize, or heart icon for each task that's due (watering, fertilization, or an overdue health check-in). The red follows `overdue_color`.
- **Linked sensors** — chips on the Overview row and rows in the expanded detail, updated live (see [Linked Sensors](#-linked-sensors-optional)).
- **Confirm Health button** — always visible in the Overview expanded detail. Shows a heart icon and reads "Update Due" when a health check-in is overdue. Color configurable.
- **Repotting** — Mark Repotted button and date input in the expanded detail view on the overview tab, with customizable button color and icon. The button and input can be hidden via the visual editor or `show_repotting` — the last repotted date always remains visible.
- **Latin / scientific name** — displays in italics below the plant name across all three tabs when enabled on a plant. Font size, color, and vertical padding all configurable.
- **Care instructions** — free-form, read-only care notes shown in the Overview expanded detail when enabled on a plant. Supports `**bold**` and line breaks; appears automatically when a plant has care text (no card config needed).
- **Narrow-card friendly** — in narrow columns the expanded detail's action buttons line up two per row with slightly smaller text, then switch to short labels (*Watered*, *Fertilized*, *Repotted*, *Confirm*) instead of stacking one per line.
- **Transparent background** — option to hide the card background, compatible with frosted glass themes
- **Pin hold button** — optionally fix the "Hold to Mark All Tasks Completed" button to the bottom of the card (the option is in the editor's Today tab section and shows while the hold button is on)
- **Choose which plants a card shows** — in the editor's **Plants** section, show only certain areas, hide individual plants, or both. Put several cards side by side, one per room. Filters apply to every tab of that card, and its hold button only completes the plants it shows; your other cards are unaffected.
- **Full visual editor** — configure everything without writing YAML. The card is also listed in the dashboard card picker.


### Card Configuration & Visual Editor

The card is fully configurable via the visual editor — no YAML required. The card can be modified via YAML if that is your preference (scroll down).

**Default configuration - no options set (all 3 tabs shown for visual reference. They are displayed one at a time by the card.):**
<img width="2912" height="1768" alt="Default card configuration: Today, Upcoming and Overview tabs" src="https://github.com/user-attachments/assets/860cf243-4a54-4e28-babe-01d823e238d5" />



```yaml
type: custom:adaptive-plant-card
```

**Custom palette — deep blue-gray background, muted sage tabs, warm amber area headers and copper label sub-headers. Max height set, latin name enabled, centered labels, pinned hold button:**

<img width="2912" height="1521" alt="Custom palette card configuration" src="https://github.com/user-attachments/assets/21cf4cb7-d1de-431d-898c-4c88fe429ded" />

```yaml
type: custom:adaptive-plant-card
height: 750
pin_hold_button: true

# Card appearance
show_background: true
card_background_color: '#1f2933'        # deep blue-gray
tab_active_color: '#8fb88a'             # muted sage — softer than the default green

# Area & label headers
area_header_size: 13
area_header_color: '#e8b86a'            # warm amber — clearly distinct from health greens
label_align: center
label_color: '#c89968'                  # softer copper — visually nested below the area header
label_header_size: 11

# Latin name
show_latin_name: true
latin_name_size: 11
latin_name_color: '#9ba8b4'             # cool gray-blue, low-contrast on purpose
latin_name_padding: 2
```

**Visual editor (shown at v19.2; v20 adds the Today tab section below) — every option is configurable without touching YAML. Customization is virtually endless:**
<p align="center">
  <img width="620" alt="Visual editor" src="https://github.com/user-attachments/assets/0188265c-fe8d-4ae0-9198-534694ab2a46" />
</p>





> *Visual editor appears as a vertical scroll - edited together because there are so many config options the vertical image was comically long. Customize away! :)*

**Today tab options (v20):**

<p align="center">
  <img width="520" alt="Today tab options in the visual editor" src="https://github.com/user-attachments/assets/83149699-0ae9-419e-8ffa-924b95080edf" />
</p>

**Plants section (v20.2) — choose which areas and plants this card shows:**

<p align="center">
  <img width="380" alt="Plants section in the visual editor" src="https://github.com/user-attachments/assets/6d938847-2633-41de-99a8-330a3f22d13e" />
</p>

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
# Plants on this card (optional; names are case-insensitive)
include_areas:            # only show plants in these areas (area IDs or names)
  - Kitchen
exclude_plants:           # hide these plants (the editor saves device IDs; plant names also work)
  - Jade
# Schedule
upcoming_days: 14         # how many days ahead to show (default: 30)
overdue_color: '#e05c5c'  # color for overdue chips and indicators
# Card appearance
show_background: true     # set false for transparent/frosted glass themes
card_background_color: #1c1c1e # optional — hex value shown represents the default
tab_active_color: #7cb97e # optional — hex value shown represents the default
show_hold_button: true    # set false to hide the "Hold to Mark All Tasks Completed" bar
pin_hold_button: false    # set true to fix hold bar to bottom of card
show_completed_today: false  # list today's finished plants under a Completed Today section
image_size: 44            # plant photo / avatar size in px (0–100, default 44; 0 hides the image)
image_shape: circle       # circle | square — square uses softly rounded corners; health ring follows
# Moisture sensor options
exclude_moisture_from_upcoming: false  # hide moisture-tracked plants from Upcoming tab
show_moisture_in_overview: false       # show live moisture % instead of watering days in Overview
show_moisture_in_today: false          # show live moisture % chip on the Today tab
show_moisture_in_upcoming: false       # show live moisture % chip on the Upcoming tab
                                       # (exclude_moisture_from_upcoming still wins on Upcoming)
# Repotting
show_repotting: true      # set false to hide button & date input (date still shown)
# Latin / scientific name
show_latin_name: false    # show italic latin name below plant name in all tabs
latin_name_size: 11       # optional — font size in px
latin_name_color: '#888888'  # optional — defaults to --secondary-text-color
latin_name_padding: 1     # optional — vertical padding in px
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
  text_today: false       # per-tab override (true / false, omit for global default)
  text_upcoming: false
  text_overview: true     # text shown on overview by default
  colors:
    excellent: '#7cb97e'
    good: '#a8cc8a'
    poor: '#e6a817'
    sick: '#e05c5c'
# Icons — use any emoji or MDI icon (e.g. mdi:water)
icons:
  water: mdi:water
  water_color: '#64b4ff'
  fertilize: mdi:flower
  fertilize_color: '#7cb97e'
  snooze: mdi:bell-sleep
  snooze_color: '#aaaaaa'
  fertilize_done: mdi:check
  fertilize_done_color: '#7cb97e'
  water_done: mdi:check
  water_done_color: '#64b4ff'
  health_confirm: 'mdi:cards-heart'       # icon for Confirm Health button
  health_confirm_color: '#aaaaaa'         # color when check-in is not overdue
  health_confirm_overdue_color: '#e05c5c' # color when check-in is overdue
  repotted_button_icon: 'mdi:pot'         # optional — emoji or MDI; omit for text-only button
  repotted_button_color: '#c8975a'        # optional — button and input focus ring color
```

All options are... they're optional — omit any to use defaults.

---

## 📋 Task Reminder Blueprint

A companion blueprint for daily plant task reminders is bundled with the integration and copied automatically into your HA blueprints directory when the integration loads — find it under Settings → Automations & Scenes → Blueprints without any manual import needed.

> **Edited the blueprint?** Your changes are kept. The integration installs the blueprint when it's missing and updates it only while it is an unmodified copy of a version that shipped with the integration. Once you edit it, it is never overwritten; to take a newer version, compare it with the one in the repository and copy over what you want (or delete your copy and restart to get a fresh one).

Sends a single combined notification when any of your plants have watering or fertilization tasks due or overdue — automatically discovering all plants without any manual configuration. Supports up to three daily reminder times, customizable notification text, an optional task count summary (e.g. "4 Waterings and 2 Fertilizations"), and a tap action to open your plant dashboard directly. Optionally restrict notifications to only fire when a person is in a specific zone. Plants can be individually excluded from watering or fertilization reminders. Compatible with the Home Assistant Companion App (iOS and Android).

> **Upgrading from v1.1.0 or earlier?** The blueprint was previously available at `blueprints/automation/adaptive_plant/plant_task_reminders.yaml` in the repo root and required manual import. It can still be imported manually from that path on those versions. From v1.2.0 onwards it is bundled and copied automatically.

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/Big-Xan/adaptive_plant/main/custom_components/adaptive_plant/blueprints/automation/plant_task_reminders.yaml)

Or manually import via **Settings → Automations & Scenes → Blueprints → Import Blueprint** and paste:
```
https://raw.githubusercontent.com/Big-Xan/adaptive_plant/main/custom_components/adaptive_plant/blueprints/automation/plant_task_reminders.yaml
```

![Task Reminder Blueprint](https://github.com/user-attachments/assets/a1c65a41-0737-4fd7-a3aa-e71e9ae2b0d5)

---

## 🧩 Templates & Scripts

Each plant is its own integration entry, so there's no built-in "all plants" sensor or button. These two template helpers and one script give you integration-wide views and actions without configuring each plant: new plants are picked up automatically.

To create a helper, go to **Settings → Devices & Services → Helpers → Create Helper → Template → Template a sensor** and paste the template into **State template**.

### Plant Tasks Today (count)

A number for dashboard badges, `numeric_state` conditions (above 0) and history graphs. Each due or overdue watering, due or overdue fertilizing, and overdue health check-in counts as one task. Name it **Plant Tasks Today** and set **State class** to **Measurement** in the helper form.

```jinja
{% set t = now().date() | string %}
{% set ns = namespace(n=0) %}
{% for e in integration_entities('adaptive_plant') | select('search', '_next_(watering|fertilization)$') %}
  {% set s = states(e) %}
  {% if s not in ['unknown', 'unavailable', ''] and s <= t %}
    {% set ns.n = ns.n + 1 %}
  {% endif %}
{% endfor %}
{% for e in integration_entities('adaptive_plant') | select('match', 'select\\..*_health$') %}
  {% if state_attr(e, 'health_check_in_overdue') %}
    {% set ns.n = ns.n + 1 %}
  {% endif %}
{% endfor %}
{{ ns.n }}
```

<img width="308" alt="Plant Tasks Today badge showing 4 tasks" src="https://github.com/user-attachments/assets/a95a1182-e9e5-4c42-b46e-3b943758cb02" />

### Plants Needing Attention (names)

A list for notification messages: one entry per plant, with its tasks grouped, e.g. `Adanson's Marge (water, fertilize), Flaming Sword (water)`. It shows `None` when nothing is due. Name it **Plants Needing Attention**. Adapted from a template shared by @pajo30 in [#32](https://github.com/Big-Xan/adaptive_plant/issues/32).

```jinja
{% set t = now().date() | string %}
{% set ns = namespace(items=[]) %}
{% for e in integration_entities('adaptive_plant') | select('search', '_next_watering$') %}
  {% set base = e[7:-14] %}
  {% set w = states(e) %}
  {% set f = states('sensor.' ~ base ~ '_next_fertilization') %}
  {% set tasks = [] %}
  {% if w not in ['unknown', 'unavailable', ''] and w <= t %}{% set tasks = tasks + ['water'] %}{% endif %}
  {% if f not in ['unknown', 'unavailable', ''] and f <= t %}{% set tasks = tasks + ['fertilize'] %}{% endif %}
  {% if state_attr('select.' ~ base ~ '_health', 'health_check_in_overdue') %}{% set tasks = tasks + ['health check'] %}{% endif %}
  {% if tasks %}
    {% set ns.items = ns.items + [(device_attr(e, 'name') or base) ~ ' (' ~ tasks | join(', ') ~ ')'] %}
  {% endif %}
{% endfor %}
{{ (ns.items | sort | join(', ') if ns.items else 'None') | truncate(255, false, '…', 0) }}
```

Home Assistant limits entity states to 255 characters, so on busy days with a large collection the list is cut off with `…`. The count helper is never affected.

<img width="408" alt="Phone notification listing the plants that need attention" src="https://github.com/user-attachments/assets/dd1256e2-715f-4737-bc33-06d01335a4bb" />

For a timed reminder, the bundled [Task Reminder Blueprint](#-task-reminder-blueprint) already sends one; use these helpers when you build your own automations or dashboards.

### Script: Complete All Due Tasks

The card's **Hold to Mark All Tasks Completed** without the card: run it from a notification action, a voice assistant, an NFC tag or a physical button. It presses each due plant's **Mark watered** / **Mark fertilized** button, exactly like the card's hold bar. Health check-ins are not completed, because the card doesn't complete them either.

Create it under **Settings → Automations & Scenes → Scripts → Add Script → ⋮ → Edit in YAML**. It needs Home Assistant 2024.8 or later; on 2024.7, change `action: button.press` to `service: button.press`.

```yaml
alias: Adaptive Plant – Complete All Due Tasks
icon: mdi:sprout
mode: single
sequence:
  - variables:
      buttons: >
        {% set t = now().date() | string %}
        {% set ns = namespace(b=[]) %}
        {% for e in integration_entities('adaptive_plant')
             | select('search', '_next_(watering|fertilization)$') %}
          {% set s = states(e) %}
          {% if s not in ['unknown', 'unavailable', ''] and s <= t %}
            {% set ns.b = ns.b + [e | replace('sensor.', 'button.')
               | regex_replace('_next_watering$', '_mark_watered')
               | regex_replace('_next_fertilization$', '_mark_fertilized')] %}
          {% endif %}
        {% endfor %}
        {{ ns.b }}
  - condition: template
    value_template: "{{ buttons | count > 0 }}"
  - action: button.press
    target:
      entity_id: "{{ buttons }}"
```

> **Note:**
> - All three find plants by their entity IDs (`_next_watering`, `_next_fertilization`, `_health`, `_mark_watered`, `_mark_fertilized`). If you rename a plant's entity IDs, or set it up in a language other than English, that plant is skipped.
> - Plants with fertilizing turned off are skipped automatically: their fertilizing sensor is `unavailable`.

---

## ❓ FAQ

**Does Adaptive Plant tell me how to take care of my plants?**

No — and that's by design. Adaptive Plant tracks and adapts to *your*
care routine rather than prescribing one. It learns your plant's actual
needs over time based on how you interact with it ("oh the soil is still wet I need to snooze it again."), but it won't tell you
that a Monstera wants indirect light or that succulents need to dry out
completely between waterings.

A plant's watering needs are influenced by a wide range of factors —
potting mix, pot size, pot type (terracotta vs. plastic vs. ceramic),
distance from the window, window direction, season, humidity, and more.
For species-specific guidance, the best starting points are:

- Houseplant subreddits (r/houseplants, r/plantclinic, and many
  species-specific communities)
- A targeted Google search for your plant's latin name
- AI assistants — just be sure to include context like potting mix,
  pot size and type, distance from window, and window direction for
  the most accurate advice

Once you have a rough watering cadence, set it as your starting interval
and let Adaptive Plant tune it from there.

---

**How do I get the tablet layout shown in the screenshot?**

Three separate cards placed side by side, each showing only one tab
(Today, Upcoming, and Overview respectively), sized to fit the tablet
screen exactly. To replicate it:

- Add three Adaptive Plant cards to a horizontal stack or grid layout
- On each card, disable the two tabs you don't want:
```yaml
  # Card 1 — Today only
  type: custom:adaptive-plant-card
  show_upcoming: false
  show_overview: false

  # Card 2 — Upcoming only
  type: custom:adaptive-plant-card
  show_today: false
  show_overview: false

  # Card 3 — Overview only
  type: custom:adaptive-plant-card
  show_today: false
  show_upcoming: false
```
- Set a `height` on each card to fill your screen and adjust widths
  to taste

---

**Can I use this without the companion card?**

Yes — the card is entirely optional. Every entity the integration creates
is a standard HA entity and works with any dashboard setup. You can use
generic HA cards like `entity`, `button`, or `history-graph` — whatever
fits your existing dashboard. The companion card just gives you a
purpose-built view with all your plants in one place, adaptive logic
visualized, and one-tap actions. The integration has no dependency on
the card.

---

**What happens if I delete a plant and re-add it?**

All state is stored in the config entry — last watered date, next
watering, fertilization dates, repotting history, notes, health, and the
adapted watering interval. Deleting the entry permanently deletes all of
that. Re-adding the plant starts completely fresh.

If you need to change a setting, always use **Configure** rather than
deleting and re-adding — almost everything is editable after setup
without losing any data.

---

**Can I get a single sensor for all my plants?**

Not as a built-in entity: each plant is its own integration entry. Two
template helpers do the job instead, one counting today's tasks and one
listing the plants that need attention, plus a script that completes
every due task at once. See [Templates & Scripts](#-templates--scripts).

---

## Privacy & Security

- Fully local — no external API calls, no telemetry, no analytics
- All state stored in config entries only
- Uploaded photos are stored outside `www/` and served only through Home Assistant's authenticated image entity proxy
- One HTTP endpoint registered to serve the bundled Lovelace card (`/adaptive_plant/adaptive-plant-card.js`) — no other endpoints exposed
> **Note:** Versions v1.1.0 and earlier registered no HTTP endpoints and required manual card and blueprint installation.
> - No shell commands executed

---

## Requirements

- Home Assistant 2024.7 or newer
- No additional Python packages required

---

## Support

If Adaptive Plant keeps your plants happy, you can support its development on Ko-fi. It's entirely optional; the integration stays free.

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/bigxan)

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built, in part, with AI.* Adaptive Plant is designed and maintained by [Big-Xan](https://github.com/Big-Xan), with development help from Claude (Anthropic).
