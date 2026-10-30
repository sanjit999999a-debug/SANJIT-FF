JOY WEBS Telegram Bot — secure setup
=====================================

IMPORTANT TOKEN SECURITY
- The token previously pasted into chat should be treated as exposed.
- Open @BotFather, revoke/regenerate that token, and use the NEW token only.
- Never share your .env file or post your token in chats/screenshots.

SETUP
1. Extract this ZIP.
2. Copy .env.example to a new file named .env.
3. Open .env and set:
   BOT_TOKEN=YOUR_NEW_TOKEN_FROM_BOTFATHER
   OWNER_ID=7774294727
   PRIVATE_CHANNEL_ID=YOUR_PRIVATE_CHANNEL_NUMERIC_ID
4. Add the bot as an administrator to both channels so Telegram permits membership checks.
5. Install dependencies: pip install -r requirements.txt
6. Run: python bot.py

Channel 1 is configured as @joy_webs.
Channel 2 is the private invite channel; PRIVATE_CHANNEL_ID must be its numeric ID (usually begins -100).
If channel membership cannot be checked, verification intentionally fails closed.

Features included:
- Premium-style welcome and reply keyboard
- ID, about, commands, status, premium, support, owner, uptime, ping
- Channel join buttons and membership verification
- SQLite user count and owner-only broadcast

Premium payment processing is not included; /premium only displays information.
