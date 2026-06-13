# ComradeBot

A self-hosted IRC bot powered by [Ollama](https://ollama.com/).

Built because IRC is still alive, local LLMs are fun, and sometimes a channel needs an opinionated robot comrade.

It joins a configured channel, keeps a small per-channel message
history in SQLite, and replies when users address it by nickname.

In addition to normal LLM conversation, ComradeBot has built-in tools for web
search, channel summaries, arithmetic, local date and time, and runtime status.

Its personality can be changed with a simple text-based system prompt.
Make it the bitter channel babushka, anxious robot or cybercop!

## Features

- Connects to IRC with optional TLS and NickServ identification.
- Uses any Ollama chat model exposed through the configured API endpoint.
- Uses a trimmed recent-history window while preserving user context.
- Limits prior bot replies and retries near-duplicate generated responses once.
- Stores up to 500 messages per network and channel in SQLite.
- Summarizes recent channel activity in three compact IRC lines.
- Searches the web through the Tavily Search API.
- Handles arithmetic and date/time questions locally without calling the LLM.
- Splits long model responses into IRC-friendly lines.
- Supports multiple IRC instances through the included systemd template.

## Commands

Commands can be entered directly in the channel and are case-insensitive.

| Command | Description |
| --- | --- |
| `!model` | Shows the configured Ollama model, temperature, `top_p`, context size, and thinking mode. |
| `!uptime` | Shows the bot process uptime and IRC network name. |
| `!status` | Shows the network, uptime, and model. |
| `!summary` | Summarizes the last 50 stored channel messages. |
| `!summary <count>` | Summarizes a requested number of messages, clamped to 10-200. |
| `!search <query>` | Returns up to three Tavily web search results. |
| `!reload_prompt` | Reloads `SYSTEM_PROMPT_FILE` after verifying an authorized NickServ account. |

### Talking to the bot

Address the configured nickname at the beginning of a message:

```text
ComradeBot: What is the difference between IRC and Matrix?
ComradeBot, recommend a short cyberpunk anime
ComradeBot explain containers in three lines
```

The nickname can also be followed by a space instead of punctuation.

### Built-in tools

These requests are handled locally when the bot is addressed:

```text
ComradeBot: what time is it?
ComradeBot: what date is it?
ComradeBot: calculate (12 + 8) * 3
ComradeBot: what is 2 ** 10?
ComradeBot: 144 / 12
```

The calculator supports `+`, `-`, `*`, `/`, `%`, `**`, parentheses, and unary
positive or negative numbers. Expressions are parsed with Python's AST rather
than evaluated as arbitrary code.

The date and time tool uses the local timezone of the machine running the bot.

### Conversation history

ComradeBot stores up to 500 messages per network and channel, but normal LLM
requests use only a recent window of up to 12 messages. User messages are kept
intact. At most two previous bot replies are included, and those replies are
shortened when necessary.

The current addressed message is sent as the user prompt rather than repeated
inside the history transcript. After generation, the reply is compared with
the bot's eight most recent replies using dependency-free text similarity. A
near-duplicate is retried once with an instruction to use substantially
different wording and avoid repeated jokes or catchphrases.

## Requirements

- Python 3
- An IRC network and channel
- A running Ollama server with a downloaded chat model
- A Tavily API key if `!search` should be available

Install the Python dependencies in a virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Ensure Ollama is running and has the desired model:

```bash
ollama pull <your_model>
```

## Configuration

ComradeBot reads configuration from environment variables. When started
directly, `python-dotenv` also loads variables from `.env`.

Create an environment file such as `my-network.env`:

```dotenv
IRC_NETWORK=ExampleNet
IRC_SERVER=irc.example.net
IRC_PORT=6697
IRC_TLS=true
IRC_CHANNEL=#example,#another-channel
IRC_NICK=BotName
IRC_PASSWORD=

OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=dolphin-mistral:latest
OLLAMA_NUM_CTX=2048
OLLAMA_NUM_PREDICT=160
OLLAMA_NUM_GPU=-1
OLLAMA_KEEP_ALIVE=30m
OLLAMA_THINK=false
OLLAMA_TEMPERATURE=0.7
OLLAMA_TOP_P=0.9

OLLAMA_SUMMARY_NUM_PREDICT=120
OLLAMA_SUMMARY_TEMPERATURE=0.1
OLLAMA_SUMMARY_TOP_P=0.6

AI_RATE_LIMIT_WINDOW=60
AI_USER_RATE_LIMIT=3
AI_CHANNEL_RATE_LIMIT=10
AI_ALLOWED_ACCOUNTS=
AI_ALLOWED_NICKS=

SYSTEM_PROMPT_FILE=/home/your-user/projects/comradebot/system_prompt.txt
ADMIN_ACCOUNTS=YourNickServAccount,AnotherAccount
TAVILY_API_KEY=
```

### Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `IRC_NETWORK` | Yes | None | Display name used to separate history and report status. |
| `IRC_SERVER` | Yes | None | IRC server hostname. |
| `IRC_CHANNEL` | Yes | None | Comma-separated channels to join. |
| `IRC_PORT` | No | `6697` | IRC server port. |
| `IRC_TLS` | No | `true` | Enables or disables TLS. |
| `IRC_NICK` | No | `ComradeBot` | Bot nickname and address prefix. |
| `IRC_PASSWORD` | No | None | Password sent to NickServ with `IDENTIFY`. |
| `OLLAMA_URL` | No | `http://localhost:11434/api/chat` | Ollama chat API endpoint. |
| `OLLAMA_MODEL` | No | `dolphin-mistral:latest` | Ollama model name. |
| `OLLAMA_NUM_CTX` | No | `2048` | Model context window requested from Ollama. |
| `OLLAMA_NUM_PREDICT` | No | `160` | Maximum tokens for normal replies. |
| `OLLAMA_NUM_GPU` | No | `-1` | Ollama GPU layer setting. |
| `OLLAMA_KEEP_ALIVE` | No | `30m` | How long Ollama keeps the model loaded. |
| `OLLAMA_THINK` | No | `false` | Ollama thinking mode: `true`, `false`, `low`, `medium`, or `high`. Disabled by default so reasoning tokens do not consume the short IRC reply budget. |
| `OLLAMA_TEMPERATURE` | No | `0.7` | Temperature for normal replies. |
| `OLLAMA_TOP_P` | No | `0.9` | Top-p value for normal replies. |
| `OLLAMA_SUMMARY_NUM_PREDICT` | No | `120` | Maximum tokens for summaries. |
| `OLLAMA_SUMMARY_TEMPERATURE` | No | `0.1` | Temperature for summaries. |
| `OLLAMA_SUMMARY_TOP_P` | No | `0.6` | Top-p value for summaries. |
| `AI_RATE_LIMIT_WINDOW` | No | `60` | Sliding rate-limit window in seconds. |
| `AI_USER_RATE_LIMIT` | No | `3` | AI requests allowed per nickname in each window. |
| `AI_CHANNEL_RATE_LIMIT` | No | `10` | AI requests allowed per channel in each window. |
| `AI_ALLOWED_ACCOUNTS` | No | None | Comma-separated NickServ accounts allowed to use AI commands. |
| `AI_ALLOWED_NICKS` | No | None | Comma-separated nicknames allowed to use AI commands. |
| `SYSTEM_PROMPT_FILE` | No | Built-in prompt | Path to a custom personality prompt. |
| `ADMIN_ACCOUNTS` | No | None | Comma-separated NickServ accounts allowed to reload the prompt. |
| `TAVILY_API_KEY` | For search | None | Enables the `!search` command. |

Keep environment files private because they may contain IRC and API
credentials. Files ending in `.env` are ignored by the included `.gitignore`.

Addressed LLM prompts, `!summary`, and `!search` share the configured per-user
and per-channel rate limits. Requests rejected by either limit do not start an
Ollama or Tavily request. Status, date/time, and calculator commands are not
rate-limited.

AI commands are public when both `AI_ALLOWED_ACCOUNTS` and `AI_ALLOWED_NICKS`
are empty. Setting either variable enables an allowlist: a user must match an
allowed NickServ account reported through IRCv3 `account-tag`, or an explicitly
allowed nickname. Account entries are safer because nicknames may be changed
or impersonated. ACL checks happen before rate-limit accounting and before any
Ollama or Tavily request.

## Running

To run directly using `.env`:

```bash
.venv/bin/python bot.py
```

To use another environment file in a shell:

```bash
set -a
source my-network.env
set +a
.venv/bin/python bot.py
```

## Running with systemd

The included `comradebot@.service` is a user-service template. Each instance
loads `%h/projects/comradebot/<instance>.env`, so an instance named `rizon`
uses `rizon.env`.

Install and start an instance:

```bash
mkdir -p ~/.config/systemd/user
cp comradebot@.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now comradebot@rizon.service
```

Useful service commands:

```bash
systemctl --user status comradebot@rizon.service
journalctl --user -u comradebot@rizon.service -f
systemctl --user restart comradebot@rizon.service
systemctl --user stop comradebot@rizon.service
```

The paths in the service file assume the repository is located at
`~/projects/comradebot`.

## Data retention and privacy

ComradeBot records channel activity to `comradebot.db`, a local SQLite
database in the bot's working directory. Each record contains the IRC network,
channel, nickname, timestamp, and message text. Bot replies are stored as well
as messages from other channel participants.

History is separated by network and channel. After each insert, the bot keeps
only the newest 500 records for that network/channel pair. Normal LLM requests
include up to the latest 30 records from the current channel. `!summary`
includes the requested number of records, between 10 and 200. Restarting the
bot does not clear this history.

SQLite data is stored as unencrypted plain text. Deleting rows does not
guarantee immediate forensic removal from the database file, filesystem,
backups, snapshots, or SQLite sidecar files. Stop the bot before deleting the
database when a complete history reset is required. Database files and their
`-wal`, `-shm`, and journal sidecars are excluded by `.gitignore` and must
never be committed.

Restrict access to the bot account and runtime files. A typical installation
should use permissions such as:

```bash
chmod 600 .env *.env comradebot.db
```

The bot's operational logs include connection status, channel names,
requesting nicknames, command types, and error details. They do not
intentionally log complete channel messages, prompts, or search queries.
When run through systemd, these logs are retained by the system journal
according to the host's journald configuration.

### Ollama data flow

When someone addresses the bot, ComradeBot sends the system prompt, their
prompt, and a trimmed window of up to 12 recent messages from that channel to
`OLLAMA_URL`. The window keeps user context while limiting prior bot replies
to two shortened entries. A generated reply that closely matches one of the
bot's eight most recent replies is retried once with a rephrasing instruction.
`!summary` sends up to 200 stored channel messages. The default Ollama URL is
local, but operators can configure a remote endpoint. A remote Ollama server
receives this channel content in plain application payloads and may apply its
own logging, retention, or privacy policy. Use HTTPS and a trusted endpoint
when Ollama is not running on the same machine.

### Tavily data flow

The `!search` command sends the user's search query to the Tavily Search API.
Recent channel history is not included. Tavily may process or retain queries
under its own terms and privacy policy. Leave `TAVILY_API_KEY` unset if search
queries must not be sent to a third party.

Operators should disclose this logging and external processing to channel
participants, obtain any consent required by local law or community policy,
and choose retention and backup practices appropriate for the channel.

To join multiple channels on one network, list them in that network's
environment file separated by commas, for example
`IRC_CHANNEL=#example,#another-channel`. A single channel remains supported.

## System prompt

If `SYSTEM_PROMPT_FILE` points to a readable file, its contents replace the
built-in conversational prompt. This repository includes `system_prompt.txt`
as an example.

After editing the file, an administrator can reload it without restarting the
bot:

```text
!reload_prompt
```

The sender must be logged into an account listed in `ADMIN_ACCOUNTS`. The bot
uses the IRCv3 `account-tag` capability where available and falls back to a
WHOIS account lookup. Nicknames alone are never accepted as proof of
authorization.

If the configured file is missing during startup, ComradeBot falls back to its
built-in prompt. The summary prompt is separate and built into `bot.py`.

## License

ComradeBot is free software licensed under the
[GNU General Public License, version 3 or later](LICENSE). You may use, modify,
and redistribute it under the terms of that license.
