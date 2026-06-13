# Changelog

All notable changes to ComradeBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [2026-06-13]

### Added

- Ollama thinking-mode configuration through `OLLAMA_THINK`.
- Unit tests for response cleanup, history trimming, duplicate detection,
  NickServ verification, and retry behavior.
- Support for Rizon's WHOIS numeric `307` when verifying identified users.

### Changed

- Reduced normal conversation context to a rolling window of up to 12
  messages.
- Limited context to at most two shortened previous bot replies while keeping
  user messages intact.
- Excluded the current addressed message from the history transcript so it is
  sent to Ollama only once.
- Added a dependency-free near-duplicate check against the bot's eight most
  recent replies.
- Retried generation once with a rephrasing instruction when a reply is too
  similar to recent output.
- Removed automatic nickname prefixes from replies and command feedback.
- Updated the example system prompt to discourage role labels, repeated
  catchphrases, and hidden reasoning output.

### Fixed

- Prevented duplicate reply prefixes such as `Pira: Pira:`.
- Removed exposed reasoning blocks emitted by models using common thinking
  tags.
- Fixed `!reload_prompt` authorization on IRC networks that report NickServ
  identification through numeric `307` instead of `330`.

### Security

- Preserved NickServ account authorization checks during WHOIS fallback by
  verifying that the returned user and host match the command sender.
