# ComradeBot

ComradeBot is a lightweight IRC bot backed by a local language model served
through [Ollama](https://ollama.com/). It joins a configured channel, keeps a
small per-channel message history in SQLite, and replies when users address it
by nickname.

In addition to normal LLM conversation, ComradeBot has built-in tools for web
search, channel summaries, arithmetic, local date and time, and runtime status.
Its personality can be changed with a text-based system prompt.

## Features

- Connects to IRC with optional TLS and NickServ identification.
- Uses any Ollama chat model exposed through the configured API endpoint.
- Includes recent channel history in LLM requests for conversational context.
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
| `!model` | Shows the configured Ollama model, temperature, `top_p`, and context size. |
| `!uptime` | Shows the bot process uptime and IRC network name. |
| `!status` | Shows the network, uptime, and model. |
| `!summary` | Summarizes the last 50 stored channel messages. |
| `!summary <count>` | Summarizes a requested number of messages, clamped to 10-200. |
| `!search <query>` | Returns up to three Tavily web search results. |
| `!reload_prompt` | Reloads `SYSTEM_PROMPT_FILE`; ignored unless the sender is listed in `ADMIN_NICKS`. |

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

## Requirements

- Python 3
- An IRC network and channel
- A running Ollama server with a downloaded chat model
- A Tavily API key if `!search` should be available

Install the Python dependencies in a virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install irc python-dotenv requests
```

Ensure Ollama is running and has the desired model:

```bash
ollama pull dolphin-mistral
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
IRC_CHANNEL=#example
IRC_NICK=ComradeBot
IRC_PASSWORD=

OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=dolphin-mistral:latest
OLLAMA_NUM_CTX=2048
OLLAMA_NUM_PREDICT=160
OLLAMA_NUM_GPU=-1
OLLAMA_KEEP_ALIVE=30m
OLLAMA_TEMPERATURE=0.7
OLLAMA_TOP_P=0.9

OLLAMA_SUMMARY_NUM_PREDICT=120
OLLAMA_SUMMARY_TEMPERATURE=0.1
OLLAMA_SUMMARY_TOP_P=0.6

SYSTEM_PROMPT_FILE=/home/your-user/projects/comradebot/system_prompt.txt
ADMIN_NICKS=YourNick,AnotherAdmin
TAVILY_API_KEY=
```

### Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `IRC_NETWORK` | Yes | None | Display name used to separate history and report status. |
| `IRC_SERVER` | Yes | None | IRC server hostname. |
| `IRC_CHANNEL` | Yes | None | Channel to join. |
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
| `OLLAMA_TEMPERATURE` | No | `0.7` | Temperature for normal replies. |
| `OLLAMA_TOP_P` | No | `0.9` | Top-p value for normal replies. |
| `OLLAMA_SUMMARY_NUM_PREDICT` | No | `120` | Maximum tokens for summaries. |
| `OLLAMA_SUMMARY_TEMPERATURE` | No | `0.1` | Temperature for summaries. |
| `OLLAMA_SUMMARY_TOP_P` | No | `0.6` | Top-p value for summaries. |
| `SYSTEM_PROMPT_FILE` | No | Built-in prompt | Path to a custom personality prompt. |
| `ADMIN_NICKS` | No | None | Comma-separated nicknames allowed to reload the prompt. |
| `TAVILY_API_KEY` | For search | None | Enables the `!search` command. |

Keep environment files private because they may contain IRC and API
credentials. Files ending in `.env` are ignored by the included `.gitignore`.

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

## Message history

Channel messages are stored in `comradebot.db`. History is separated by IRC
network and channel, and only the newest 500 messages for each pair are kept.
Normal LLM replies receive the latest 30 messages as context. `!summary` reads
the requested number of messages from the same history.

Messages are stored in plain text. Anyone operating the bot should treat the
database as channel logs and apply the privacy and retention expectations of
the IRC community where it is used.

## System prompt

If `SYSTEM_PROMPT_FILE` points to a readable file, its contents replace the
built-in conversational prompt. This repository includes `system_prompt.txt`
as an example.

After editing the file, an administrator can reload it without restarting the
bot:

```text
!reload_prompt
```

If the configured file is missing during startup, ComradeBot falls back to its
built-in prompt. The summary prompt is separate and built into `bot.py`.
