# 🟣Telegram Live Alert Bot

A Telegram bot for managing live-session alerts in an ApexTrade AI community group.

The bot allows the owner to control live alerts through an interactive button-based panel. When **LIVE MODE** is activated, the bot automatically sends randomized live-session messages to the configured Telegram group at a selected interval and automatically deletes each alert after a configurable amount of time.

## ✨ Features

- 🔴 Start and stop LIVE MODE
- ⏱ Configurable alert intervals
- 🗑 Automatic message deletion
- 💬 Add, view, and remove alert messages
- 🎯 Configure a target Telegram group
- 📊 View current bot status
- 🎛️ Interactive inline-button control panel
- 🔐 Owner-only controls
- 💾 Persistent configuration using JSON
- 🎲 Randomized alert messages
- 🚫 Prevents the same alert from appearing consecutively
- 🤖 Runs continuously using Telegram polling

## 🛠️ Tech Stack

- Python
- python-telegram-bot
- Telegram Bot API
- python-dotenv
- JSON configuration storage

## 📋 Setup

### 1. Clone the repository

```bash
git clone https://github.com/vhemmsley/TG-Live-Alert-Bot.git
cd YOUR_REPOSITORY
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your `.env` file

```env
BOT_TOKEN=YOUR_BOT_TOKEN
OWNER_ID=YOUR_TELEGRAM_USER_ID
```

### 4. Add the bot to your Telegram group

Add the bot to the group where you want the live alerts to appear and make it an **administrator**.

The bot needs permission to:

- Send messages
- Delete messages

### 5. Register the target group

Inside the Telegram group, send:

```text
/setgroup
```

The bot will save that group as the target for live alerts.

### 6. Open the control panel

You can then privately message the bot and send:

```text
/panel
```

or:

```text
/start
```

The interactive control panel will appear.

## 🎛️ Control Panel

From the panel you can control:

**🔴 START LIVE**
Starts automatic live-session alerts.

**⏹ STOP LIVE**
Stops all future alerts.

**⏱ INTERVAL**
Choose how frequently alerts are sent.

**🗑 DELETE AFTER**
Choose how long each alert remains visible.

**💬 MESSAGES**
View, add, or remove alert messages.

**🎯 TARGET GROUP**
View the currently configured target group.

**📊 STATUS**
View the current bot configuration and live status.

## ⚙️ Configuration

The bot automatically creates `config.json` and stores settings such as:

- Target group
- Alert interval
- Delete delay
- Alert messages
- Live mode status

No database is required.

## 🚀 Running the Bot

Start the bot with:

```bash
python bot.py
```

The bot will begin polling Telegram and remain active until the process is stopped.

## 🟣 ApexTrade AI

**Analyze. Execute. Ascend In Profit 🟣**
