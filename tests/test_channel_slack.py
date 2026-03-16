"""Tests for core/channels/slack.py — Slack Bot DM channel."""
import json
import socket
from unittest.mock import patch, MagicMock
from urllib.error import URLError, HTTPError

import pytest

from core.channels.slack import send


class TestSlackValidation:
    """Tests for config validation before sending."""

    def test_missing_slack_config_logs_warning(self, capsys):
        send("title", "msg", {}, {})
        err = capsys.readouterr().err
        assert "not configured" in err

    def test_missing_slack_config_does_not_raise(self):
        send("title", "msg", {}, {})

    def test_missing_bot_token_logs_warning(self, capsys):
        send("title", "msg", {}, {"slack": {"user_id": "U123"}})
        err = capsys.readouterr().err
        assert "not configured" in err

    def test_missing_user_id_logs_warning(self, capsys):
        send("title", "msg", {}, {"slack": {"bot_token": "xoxb-test"}})
        err = capsys.readouterr().err
        assert "not configured" in err

    def test_empty_bot_token_logs_warning(self, capsys):
        send("title", "msg", {}, {"slack": {"bot_token": "", "user_id": "U123"}})
        assert capsys.readouterr().err


class TestSlackSend:
    """Tests for successful Slack API calls."""

    @patch("urllib.request.urlopen")
    def test_calls_conversations_open_and_post_message(self, mock_urlopen):
        open_response = MagicMock()
        open_response.read.return_value = json.dumps({"ok": True, "channel": {"id": "D999"}}).encode()
        open_response.__enter__ = lambda s: s
        open_response.__exit__ = MagicMock(return_value=False)

        post_response = MagicMock()
        post_response.read.return_value = json.dumps({"ok": True}).encode()
        post_response.__enter__ = lambda s: s
        post_response.__exit__ = MagicMock(return_value=False)

        mock_urlopen.side_effect = [open_response, post_response]

        config = {"slack": {"bot_token": "xoxb-test-token", "user_id": "U123ABC"}}
        send("Claude is waiting", "Project: my-api", {}, config)

        assert mock_urlopen.call_count == 2

        first_call = mock_urlopen.call_args_list[0]
        req1 = first_call[0][0]
        assert "conversations.open" in req1.full_url
        body1 = json.loads(req1.data)
        assert body1["users"] == "U123ABC"

        second_call = mock_urlopen.call_args_list[1]
        req2 = second_call[0][0]
        assert "chat.postMessage" in req2.full_url
        body2 = json.loads(req2.data)
        assert body2["channel"] == "D999"
        assert "Claude is waiting" in body2["text"]

    @patch("urllib.request.urlopen")
    def test_includes_auth_header(self, mock_urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({"ok": True, "channel": {"id": "D1"}}).encode()
        response.__enter__ = lambda s: s
        response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = response

        config = {"slack": {"bot_token": "xoxb-my-token", "user_id": "U1"}}
        send("t", "m", {}, config)

        req = mock_urlopen.call_args_list[0][0][0]
        assert req.get_header("Authorization") == "Bearer xoxb-my-token"


class TestSlackErrors:
    """Tests for error handling — network errors, API errors."""

    @patch("urllib.request.urlopen")
    def test_network_error_does_not_raise(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("connection refused")
        config = {"slack": {"bot_token": "xoxb-test", "user_id": "U1"}}
        send("t", "m", {}, config)

    @patch("urllib.request.urlopen")
    def test_network_error_logs_warning(self, mock_urlopen, capsys):
        mock_urlopen.side_effect = URLError("connection refused")
        config = {"slack": {"bot_token": "xoxb-test", "user_id": "U1"}}
        send("t", "m", {}, config)
        assert capsys.readouterr().err

    @patch("urllib.request.urlopen")
    def test_http_error_does_not_raise(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError("url", 403, "forbidden", {}, None)
        config = {"slack": {"bot_token": "xoxb-test", "user_id": "U1"}}
        send("t", "m", {}, config)

    @patch("urllib.request.urlopen")
    def test_timeout_does_not_raise(self, mock_urlopen):
        mock_urlopen.side_effect = socket.timeout("timed out")
        config = {"slack": {"bot_token": "xoxb-test", "user_id": "U1"}}
        send("t", "m", {}, config)
