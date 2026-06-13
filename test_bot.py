from collections import defaultdict
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("IRC_NETWORK", "test")
os.environ.setdefault("IRC_SERVER", "irc.example")
os.environ.setdefault("IRC_CHANNEL", "#test")

from bot import (
    ComradeBot,
    ask_llm,
    format_chat_history,
    is_near_duplicate_reply,
    replies_are_near_duplicates,
    trim_chat_history,
)
from model_response import (
    clean_model_response,
    parse_think_setting,
    strip_nick_prefix,
)


class ParseThinkSettingTests(unittest.TestCase):
    def test_parses_boolean_values(self):
        self.assertIs(parse_think_setting("false"), False)
        self.assertIs(parse_think_setting("YES"), True)

    def test_parses_thinking_levels(self):
        self.assertEqual(parse_think_setting(" Medium "), "medium")

    def test_rejects_invalid_value(self):
        with self.assertRaisesRegex(ValueError, "OLLAMA_THINK"):
            parse_think_setting("sometimes")


class CleanModelResponseTests(unittest.TestCase):
    def test_returns_clean_response_unchanged(self):
        self.assertEqual(
            clean_model_response("A normal conversational reply."),
            "A normal conversational reply.",
        )

    def test_removes_multiline_reasoning_block(self):
        response = (
            "<think>\nI should reason about this first.\n</think>\n"
            "Here is the answer."
        )

        self.assertEqual(
            clean_model_response(response),
            "Here is the answer.",
        )

    def test_removes_multiple_reasoning_tag_styles(self):
        response = (
            "<analysis>analysis text</analysis>"
            "Clean answer"
            "<reasoning mode=\"hidden\">reasoning text</reasoning>"
        )

        self.assertEqual(clean_model_response(response), "Clean answer")

    def test_removes_nested_reasoning_blocks(self):
        response = (
            "<think>outer <think>inner</think> reasoning</think>"
            "Final answer"
        )

        self.assertEqual(clean_model_response(response), "Final answer")

    def test_hides_content_after_unclosed_reasoning_tag(self):
        response = "<THINK>draft text\nFinal answer"

        self.assertEqual(clean_model_response(response), "")

    def test_removes_reasoning_before_orphan_closing_tag(self):
        response = (
            "We need answer briefly.\n"
            "</think>\n\n"
            "Clean final answer."
        )

        self.assertEqual(
            clean_model_response(response),
            "Clean final answer.",
        )


class StripNickPrefixTests(unittest.TestCase):
    def test_removes_model_generated_nick_prefix(self):
        self.assertEqual(
            strip_nick_prefix("Pira: Packet successfully delivered.", "Pira"),
            "Packet successfully delivered.",
        )

    def test_removes_repeated_nick_prefixes(self):
        self.assertEqual(
            strip_nick_prefix("Pira: Pira: Works on my machine.", "Pira"),
            "Works on my machine.",
        )

    def test_matches_nick_case_insensitively(self):
        self.assertEqual(
            strip_nick_prefix("pIRA, Peak UNIX behavior.", "Pira"),
            "Peak UNIX behavior.",
        )

    def test_preserves_nick_mentioned_later(self):
        self.assertEqual(
            strip_nick_prefix("That belongs to Pira: probably.", "Pira"),
            "That belongs to Pira: probably.",
        )


class ChatHistoryTests(unittest.TestCase):
    def test_limits_history_and_downsamples_bot_replies(self):
        rows = [
            (f"2026-06-13 10:{index:02d}:00", nick, message)
            for index, (nick, message) in enumerate(
                [
                    ("Alice", "user message 1"),
                    ("ComradeBot", "bot reply 1"),
                    ("Bob", "user message 2"),
                    ("ComradeBot", "bot reply 2"),
                    ("Alice", "user message 3"),
                    ("ComradeBot", "bot reply 3"),
                    ("Bob", "user message 4"),
                    ("ComradeBot", "bot reply 4"),
                    ("Alice", "user message 5"),
                ]
            )
        ]

        trimmed = trim_chat_history(
            rows,
            "ComradeBot",
            max_messages=6,
            max_bot_messages=2,
        )

        self.assertEqual(len(trimmed), 6)
        self.assertEqual(
            [message for _, nick, message in trimmed if nick == "ComradeBot"],
            ["bot reply 3", "bot reply 4"],
        )
        self.assertEqual(
            [message for _, nick, message in trimmed if nick != "ComradeBot"],
            [
                "user message 2",
                "user message 3",
                "user message 4",
                "user message 5",
            ],
        )

    def test_shortens_bot_replies_but_preserves_user_messages(self):
        long_user_message = "user " * 20
        long_bot_message = "bot " * 20
        rows = [
            ("2026-06-13 10:00:00", "Alice", long_user_message),
            ("2026-06-13 10:01:00", "ComradeBot", long_bot_message),
        ]

        trimmed = trim_chat_history(
            rows,
            "ComradeBot",
            bot_message_max_chars=20,
        )

        self.assertEqual(trimmed[0][2], long_user_message)
        self.assertLessEqual(len(trimmed[1][2]), 23)
        self.assertTrue(trimmed[1][2].endswith("..."))

    def test_excludes_only_the_latest_current_request(self):
        rows = [
            ("2026-06-13 10:00:00", "Pira", "ComradeBot: hello"),
            ("2026-06-13 10:01:00", "Other", "unrelated"),
            ("2026-06-13 10:02:00", "Pira", "ComradeBot: hello"),
        ]

        trimmed = trim_chat_history(
            rows,
            "ComradeBot",
            exclude_latest=("Pira", "ComradeBot: hello"),
        )

        self.assertEqual(
            format_chat_history(trimmed).count("ComradeBot: hello"),
            1,
        )


class DuplicateReplyTests(unittest.TestCase):
    def test_detects_exact_reply_ignoring_case_and_punctuation(self):
        self.assertTrue(
            replies_are_near_duplicates(
                "Packet successfully delivered!",
                "packet successfully delivered.",
            )
        )

    def test_detects_near_duplicate_catchphrase(self):
        self.assertTrue(
            replies_are_near_duplicates(
                "The spaghetti has achieved sentience again.",
                "The spaghetti has achieved sentience.",
            )
        )

    def test_allows_distinct_reply(self):
        self.assertFalse(
            replies_are_near_duplicates(
                "Hello. What are you working on?",
                "Packet successfully delivered.",
            )
        )

    def test_checks_candidate_against_recent_replies(self):
        self.assertTrue(
            is_near_duplicate_reply(
                "Works on my machine.",
                [
                    "Something unrelated.",
                    "Well, works on my machine!",
                ],
            )
        )


class AskLlmRetryTests(unittest.TestCase):
    @patch("bot.get_recent_bot_replies")
    @patch("bot.get_channel_context")
    @patch("bot.request_ollama_chat")
    def test_retries_once_when_reply_matches_recent_history(
        self,
        request_chat,
        get_context,
        get_recent_replies,
    ):
        get_context.return_value = "Alice: hello"
        get_recent_replies.return_value = ["Packet successfully delivered."]
        request_chat.side_effect = [
            "Packet successfully delivered!",
            "Hello. What are you working on?",
        ]

        reply = ask_llm(
            "hello",
            "test",
            "#test",
            "Alice",
            "ComradeBot: hello",
        )

        self.assertEqual(reply, "Hello. What are you working on?")
        self.assertEqual(request_chat.call_count, 2)
        retry_messages = request_chat.call_args_list[1].args[0]
        self.assertEqual(
            retry_messages[-2],
            {"role": "assistant", "content": "Packet successfully delivered!"},
        )
        self.assertIn(
            "substantially different wording",
            retry_messages[-1]["content"],
        )
        get_context.assert_called_once_with(
            "test",
            "#test",
            exclude_latest=("Alice", "ComradeBot: hello"),
        )

    @patch("bot.get_recent_bot_replies")
    @patch("bot.get_channel_context")
    @patch("bot.request_ollama_chat")
    def test_does_not_retry_a_distinct_reply(
        self,
        request_chat,
        get_context,
        get_recent_replies,
    ):
        get_context.return_value = ""
        get_recent_replies.return_value = ["Packet successfully delivered."]
        request_chat.return_value = "Hello. What are you working on?"

        reply = ask_llm(
            "hello",
            "test",
            "#test",
            "Alice",
            "ComradeBot: hello",
        )

        self.assertEqual(reply, "Hello. What are you working on?")
        request_chat.assert_called_once()


class ReloadPromptVerificationTests(unittest.TestCase):
    def setUp(self):
        self.bot = ComradeBot.__new__(ComradeBot)
        self.bot.pending_admin_commands = defaultdict(list)
        self.bot.whois_accounts = {}
        self.bot.whois_identities = {}
        self.bot.whois_identified_nicks = set()
        self.connection = SimpleNamespace(privmsg=lambda *args: None)

    def test_accepts_rizon_307_for_matching_sender_identity(self):
        self.bot.pending_admin_commands["pira"].append(
            ("Pira", "#test", "user", "host")
        )
        self.bot.whois_identities["pira"] = ("user", "host")
        verified = []
        self.bot.run_reload_prompt = (
            lambda connection, nick, channel, account:
            verified.append((nick, channel, account))
        )

        self.bot.on_307(
            self.connection,
            SimpleNamespace(arguments=["Pira", "has identified for this nick"]),
        )
        self.bot.on_endofwhois(
            self.connection,
            SimpleNamespace(arguments=["Pira", "End of /WHOIS list."]),
        )

        self.assertEqual(verified, [("Pira", "#test", "Pira")])

    def test_rejects_rizon_307_when_sender_identity_changed(self):
        self.bot.pending_admin_commands["pira"].append(
            ("Pira", "#test", "original-user", "original-host")
        )
        self.bot.whois_identities["pira"] = ("other-user", "other-host")
        verified = []
        self.bot.run_reload_prompt = lambda *args: verified.append(args)

        self.bot.on_307(
            self.connection,
            SimpleNamespace(arguments=["Pira", "has identified for this nick"]),
        )
        self.bot.on_endofwhois(
            self.connection,
            SimpleNamespace(arguments=["Pira", "End of /WHOIS list."]),
        )

        self.assertEqual(verified, [])


if __name__ == "__main__":
    unittest.main()
