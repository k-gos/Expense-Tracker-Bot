# Serverless Cloud Expense Tracker

A highly secure, private, and fully automated personal expense tracker. It uses a **Telegram Bot** for natural language input (via webhooks) and a **zero-dependency static HTML dashboard** for offline-capable visualizations. 

Data is stored in a lightweight SQLite database. The architecture is designed to be hosted entirely on free-tier cloud platforms (like PythonAnywhere) without exposing any database ports or relying on expensive cloud services.

---

## Architecture
1. **Telegram Client:** User sends natural language text (e.g., `"spent 500 on swiggy"`).
2. **Flask Webhook (`flask_app.py`):** Receives the payload via a secure, unguessable webhook URL. Authenticates the request against a whitelisted `Chat ID`.
3. **NLP Parser (`parser.py`):** Extracts amounts using Regex (handles formats like `1.5k`, `2l`, `rs 500`) and categorizes the transaction based on dynamic keywords stored in `config.json`.
4. **SQLite Storage (`db.py`):** Commits the transaction to `expenses.db`.
5. **Static Exporter (`export.py`):** Dumps the entire database and config limits into a static Javascript file (`data.js`).
6. **Frontend Dashboard (`dashboard.html`):** A static HTML file served by Flask (behind HTTP Basic Auth) that reads `data.js` to render interactive SVG charts and metrics without requiring external JS libraries or APIs.

---

## Key Features
- **Natural Language Processing:** Parses messy strings into structured JSON `{amount, category, note, type}`.
- **Automated Bill Splitting:** `"paid 600 for cab me, alice, bob"` splits the bill 3 ways, logs your share as an expense, and logs the rest under `money given`.
- **Dynamic Learning:** Train the bot dynamically via Telegram. Command `/addkeyword dominos` lets you map 'dominos' to an existing category, permanently updating the config.
- **On-the-fly Budgets:** Command `/addbudget travel 8000` updates your monthly limits instantly.
- **Strict Security:** 
  - Bot ignores all messages except from your exact Telegram `Chat ID`.
  - Dashboard is locked behind HTTP Basic Authentication.
- **Zero-Dependency Frontend:** All charts (Donuts, Progress bars) are drawn using inline SVGs and vanilla Javascript. No React, no Chart.js, no CDNs.

---

## Project Structure
```text
├── config.json        # Central config: Tokens, credentials, budgets, and keywords
├── dashboard.html     # The visual frontend
├── db.py              # SQLite database wrapper
├── export.py          # Serializes DB to data.js for the frontend
├── flask_app.py       # Main WSGI server & Webhook handler
├── parser.py          # Regex & categorization logic
└── requirements.txt   # Python dependencies
```

---

## Setup & Deployment Guide

### 1. Initial Configuration
1. Open `config.json`.
2. Set your custom `dashboard_username` and `dashboard_password`.
3. Set your initial budgets (you can change these later via the bot).

### 2. Get Telegram Credentials
1. Message **@BotFather** on Telegram and send `/newbot`.
2. Copy the **HTTP API Token** he provides.
3. Paste the token into `config.json` under `"telegram_token"`.

### 3. Local Testing & Getting your Chat ID
You need your personal Telegram Chat ID to whitelist yourself.
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # (On Windows: .\venv\Scripts\activate)
   pip install -r requirements.txt
   ```
2. Run the server locally:
   ```bash
   python flask_app.py
   ```
3. Send `/start` to your bot on Telegram. It will reply with your Chat ID.
4. Copy the Chat ID into `config.json` under `"allowed_chat_id"`.
5. Kill the local server (`Ctrl + C`).

### 4. Cloud Deployment (PythonAnywhere)
1. Create a free account on [PythonAnywhere](https://www.pythonanywhere.com/).
2. In the **Files** tab, upload all files into the `mysite` folder.
3. In the **Web** tab, create a new **Flask** app (select your preferred Python version, e.g., 3.12).
4. Edit the WSGI configuration file (link found in the Web tab) to ensure it points to your directory:
   ```python
   import sys
   import os
   
   project_home = '/home/yourusername/mysite'
   if project_home not in sys.path:
       sys.path = [project_home] + sys.path
   
   os.chdir(project_home) # Crucial for relative file paths
   
   from flask_app import app as application
   ```
5. In the **Consoles** tab, open a Bash terminal and install the Telegram library for your specific Python version:
   ```bash
   pip3.12 install pyTelegramBotAPI --user
   ```
6. **Reload** the web app from the Web tab.

### 5. Set the Webhook
To tell Telegram where your server is, visit this URL in your browser **once** (replace with your actual token and username):
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://<yourusername>.pythonanywhere.com/<YOUR_BOT_TOKEN>
```
You should see `{"ok":true,"result":true,"description":"Webhook was set"}`.

---

## Bot Commands
- `/total` - View your total spend vs monthly budget limit.
- `/budget` - View all active category limits.
- `/addbudget <category> <amount>` - Set or update a monthly cap.
- `/addkeyword <word>` - Teach the NLP parser a new keyword interactively.
- `/undo` - Deletes your most recent transaction.
