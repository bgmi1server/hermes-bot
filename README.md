# Hermes Bot Setup Guide

Welcome to the Hermes Bot! Follow these simple steps to set up and run your bot on Windows.

## Prerequisites

Before starting, you'll need:
1. A Telegram account.
2. Python installed on your Windows machine.

## Step 1: Get a Telegram Bot Token

1. Open Telegram and search for **BotFather** (it has a verified blue checkmark).
2. Start a chat with BotFather and send the command `/newbot`.
3. Follow the prompts to choose a name and a username for your bot. The username must end in `bot` (e.g., `MyAwesome_bot`).
4. Once created, BotFather will give you a **Bot Token** (a long string of characters like `123456789:ABCDEF...`). 
5. Copy this token and keep it secure. You will need it in Step 3.

## Step 2: Get your Telegram User ID

To allow the bot to recognize you as an authorized user, you need your Telegram User ID.
1. Open Telegram and search for **@userinfobot** or **@RawDataBot**.
2. Start a chat and it will reply with your User ID (a number like `123456789`).
3. Copy this ID. You will need it in Step 3.

## Step 3: Configure the Bot

1. Open the `hermes_bot` folder.
2. Find the file named `config.py`.
3. Right-click on `config.py` and open it with a text editor (like Notepad).
4. Replace the placeholders with your actual Bot Token and User ID.
5. Save and close the file.

## Step 4: Install the Environment

1. In the `hermes_bot` folder, locate the file named `install.bat`.
2. **Double-click `install.bat`**.
3. A command prompt window will open and automatically install all the necessary requirements for your bot. Wait for the process to finish.

## Step 5: Start the Bot

1. In the same folder, locate the file named `start_bot.bat`.
2. **Double-click `start_bot.bat`**.
3. A command prompt window will stay open, indicating that your bot is running.
4. Go to Telegram, find your bot, and send a message to start interacting with it!

Enjoy using Hermes Bot!
