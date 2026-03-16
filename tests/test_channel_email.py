"""Tests for core/channels/email.py — email placeholder channel."""
from core.channels.email import send


class TestEmailChannel:
    """Tests for the email placeholder."""

    def test_send_logs_warning(self, capsys):
        """Should log a warning that email is not yet implemented."""
        send("title", "message", {}, {})
        assert "not yet implemented" in capsys.readouterr().err

    def test_send_does_not_raise(self):
        """Should never raise, even with empty config."""
        send("title", "message", {}, {})

    def test_send_returns_none(self):
        """Should return None."""
        result = send("title", "message", {}, {})
        assert result is None
