"""
Unit tests for StubPushSender: send_sign_request appends events; get_pending_events returns them.

Task: task-implement-push-sender-interface-stub.
"""

import pytest

from services.wallet_push import StubPushSender


class TestStubPushSender:
    def test_send_sign_request_appends_event(self):
        stub = StubPushSender()
        stub.send_sign_request("user-1", "sign_arweave", "upload-uuid-1")
        events = stub.get_pending_events()
        assert len(events) == 1
        assert events[0]["user_id"] == "user-1"
        assert events[0]["request_type"] == "sign_arweave"
        assert events[0]["request_id"] == "upload-uuid-1"
        assert "timestamp" in events[0]

    def test_two_calls_yield_two_events_with_correct_fields(self):
        stub = StubPushSender()
        stub.send_sign_request("user-1", "sign_arweave", "upload-uuid-1")
        stub.send_sign_request("user-2", "sign_contract", "req-456")
        events = stub.get_pending_events()
        assert len(events) == 2
        assert events[0]["user_id"] == "user-1"
        assert events[0]["request_type"] == "sign_arweave"
        assert events[0]["request_id"] == "upload-uuid-1"
        assert events[1]["user_id"] == "user-2"
        assert events[1]["request_type"] == "sign_contract"
        assert events[1]["request_id"] == "req-456"

    def test_get_pending_events_returns_copy(self):
        stub = StubPushSender()
        stub.send_sign_request("u", "sign_arweave", "r1")
        first = stub.get_pending_events()
        second = stub.get_pending_events()
        assert first is not second
        assert first == second

    def test_clear_pending_empties_events(self):
        stub = StubPushSender()
        stub.send_sign_request("u", "sign_arweave", "r1")
        stub.clear_pending()
        assert len(stub.get_pending_events()) == 0
