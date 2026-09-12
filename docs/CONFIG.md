# Configuration Guide (YAML & JSON)

This project relies on configuration files to manage business rules, delivery zones, payment gateways, frontend visuals, and translations without requiring code changes.

## Table of Contents
1. [Important Rule: Reloading Config](#important-rule-reloading-config)
2. [Business Configurations (YAML)](#1-business-configurations-yaml)
3. [Frontend Configurations (YAML)](#2-frontend-configurations-yaml)
4. [Localization & Translations (JSON)](#3-localization--translations-json)

---

## Important Rule: Reloading Config

⚠️ **CRITICAL:** The backend caches these configuration files in memory for performance. 
After making **any** changes to the `.yaml` or `.json` files, you **MUST** run the following command to apply them:
`make reload-config`

---

## 1. Business Configurations (YAML)

These files control the core domain logic and are loaded by the backend services.

### `basket.yaml`
Controls shopping cart limits.
* `limit_on_the_number_of_items`: Maximum number of distinct items a user can have in their basket at one time.

### `delivery.yaml`
Manages shipping costs and regional multipliers.
* Defines the `base_rate`, cost per kilogram (`rete_per_kg`), and thresholds for free shipping.
* **Zone Multipliers (`zone_multipliers`)**: A flexible geographic configuration. 
  > 💡 **Important:** You can freely customize these zones! If you don't ship to specific countries or states, simply delete them from the list. Conversely, you can add new zones or expand existing ones based on your business needs.

### `notification.yaml`
Configures where and how system notifications are routed.
* Supports routing via Telegram, Email, or Webhooks.
  > 💡 **Recommendation:** We highly recommend leaving `telegram` as the default provider for all notification types. 
  > ⚠️ **Note:** The `support` channel notifications currently **only** support the `telegram` provider.

### `order.yaml`
Defines the lifecycle and limitations of orders and promotional codes.
* Limits how many unpaid orders a user can hold (`order_pending_limit`).
* Defines how long an order waits for payment before expiring (`order_lifetime_minutes`).

### `payments.yaml` 💳 (Critical)
Manages payment gateways, fees, and network settings.
* **`is_testnet`**: ⚠️ **CRITICAL SETTING**. 
  * Set `is_testnet: True` during development and testing to use Sandbox environments.
  * Set `is_testnet: False` **ONLY** when you are deploying to production and are ready to accept real money.
* Defines minimum order amounts and buyer fee coverage.
* Configures accepted coins and networks.

### `support.yaml`
Controls the support ticketing system limits (e.g., maximum active tickets per user) and auto-closure policies.

### `user.yaml`
Sets the default preferences for new users (preferred cryptocurrency, network, and UI themes).

---

## 2. Frontend Configurations (YAML)

These files control the visual presentation and UI text in the Telegram Mini App (TMA).

### `background.yaml`
Defines the CSS background properties (gradients, colors) for both Dark and Light themes.

### `footer.yaml`
Controls the legal and support information displayed at the bottom of the Web App.
  > 💡 **Pro Tip for Legal Links:** You can write your Privacy Policy or Terms of Service quickly and for free using [Telegra.ph](https://telegra.ph/), publish it, and paste the generated link here.

### `particles.yaml`
Configures the interactive background particle animation (speed, density, mouse interaction).

### `payments_visual.yaml`
Maps the backend payment configuration to frontend visuals (display names, SVG URLs). Ensure this matches your backend `payments.yaml` logic.

### `zone_names_extra.yaml`
Provides UI metadata for the delivery zones defined in `delivery.yaml`.
* Used to display the estimated `delivery_days` to the customer based on their region.
  > 💡 **Important:** Just like `delivery.yaml`, this list is fully dynamic. If you removed or added zones in the business configuration, you must add or remove them here as well.

---

## 3. Localization & Translations (JSON)

Text for the frontend interfaces and bot notifications is stored in JSON files. 
The primary source of truth is the English base file.

### `en.json` (The Master File)
* This file contains the base English text for the shop page, cart page, checkout page, admin notifications, and user notifications.
* It includes keys for UI elements like filters, buttons, modal titles, and error messages.

### Auto-Translation Logic
The project includes a translation script (`make translate-all LANG=<code_name>`) that uses AI to translate your base texts into other languages.
* **How it works:** If a translation key in the target language JSON is empty, the translator will automatically translate the text from `en.json` and fill it in.
* **Manual Overrides:** If a key already contains text, the auto-translator will **skip** it. This means you can manually correct or change any translated text without fear of it being overwritten during the next auto-translation run.

### Adding a New Language
If you want to support a new language, generating the JSON is not enough. You must explicitly enable it in the Django settings.

1. Open `backend/config/settings.py`.
2. Locate the `LANGUAGES` array.
3. Add your new language tuple to the list. For example:
   ```python
   LANGUAGES = [
       ("ru", "Русский"),
       ("en", "English"),
       ("es", "Español"),
       ("uk", "Українська"),
       ("cs", "Čeština"),
       ("de", "Deutsch"),
       # Add your new language here:
       ("fr", "Français"),
   ]
   ```
   Restart the backend containers and run `make reload-config`
