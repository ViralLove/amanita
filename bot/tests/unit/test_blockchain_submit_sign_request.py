"""
Unit tests: BlockchainService.submit_sign_request_raw_transaction — проверка chain/`to` и broadcast.

Покрывает критический путь подписания (не только мок роутера): несовпадение сети/контракта → ValueError;
успех → вызов web3.eth.send_raw_transaction с теми же байтами.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from hexbytes import HexBytes
from web3 import Web3

from bot.services.core.blockchain import BlockchainService


def _sign_type2_tx(*, chain_id: int, to_addr: str) -> str:
    w3 = Web3()
    acct = w3.eth.account.create()
    tx = {
        "chainId": chain_id,
        "gas": 21000,
        "maxFeePerGas": w3.to_wei(2, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "nonce": 0,
        "to": Web3.to_checksum_address(to_addr),
        "value": 0,
        "type": 2,
        "data": b"",
    }
    signed = w3.eth.account.sign_transaction(tx, acct.key)
    return "0x" + signed.raw_transaction.hex()


@pytest.fixture
def submit_service(monkeypatch):
    """Минимальный BlockchainService без RPC/реестра — только web3-метод broadcast."""
    BlockchainService.reset()
    mock_web3 = MagicMock()
    mock_web3.eth.send_raw_transaction.return_value = HexBytes(b"\xcd" * 32)

    def minimal_init(self):
        self.web3 = mock_web3
        self.chain_id = 137
        self._initialized = True

    monkeypatch.setattr(BlockchainService, "__init__", minimal_init)
    svc = BlockchainService()
    return svc, mock_web3


@pytest.mark.unit
class TestSubmitSignRequestRawTransaction:
    def test_success_calls_send_raw_with_same_bytes(self, submit_service):
        svc, mock_web3 = submit_service
        to_hex = "0x" + "22" * 20
        raw_hex = _sign_type2_tx(chain_id=137, to_addr=to_hex)
        tx_bytes = bytes.fromhex(raw_hex[2:])

        out = svc.submit_sign_request_raw_transaction(
            raw_hex,
            expected_chain_id="137",
            expected_to_address=to_hex,
        )

        assert out == "cd" * 32
        mock_web3.eth.send_raw_transaction.assert_called_once()
        (sent,), _ = mock_web3.eth.send_raw_transaction.call_args
        assert sent == tx_bytes

    def test_rejects_chain_id_mismatch(self, submit_service):
        svc, mock_web3 = submit_service
        to_hex = "0x" + "33" * 20
        raw_hex = _sign_type2_tx(chain_id=137, to_addr=to_hex)

        with pytest.raises(ValueError, match="does not match sign request context"):
            svc.submit_sign_request_raw_transaction(
                raw_hex,
                expected_chain_id="1",
                expected_to_address=to_hex,
            )
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_rejects_to_mismatch(self, submit_service):
        svc, mock_web3 = submit_service
        signed_to = "0x" + "44" * 20
        expected_to = "0x" + "55" * 20
        raw_hex = _sign_type2_tx(chain_id=137, to_addr=signed_to)

        with pytest.raises(ValueError, match="does not match expected contract"):
            svc.submit_sign_request_raw_transaction(
                raw_hex,
                expected_chain_id="137",
                expected_to_address=expected_to,
            )
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_localhost_mock_hex_returns_without_send_raw(self, monkeypatch, submit_service):
        svc, mock_web3 = submit_service
        monkeypatch.setenv("BLOCKCHAIN_PROFILE", "localhost")
        mock_hex = "0x" + "00" * 64
        out = svc.submit_sign_request_raw_transaction(
            mock_hex,
            expected_chain_id="137",
            expected_to_address="0x" + "66" * 20,
        )
        assert out == "0x" + "00" * 32
        mock_web3.eth.send_raw_transaction.assert_not_called()

    def test_invalid_hex_raises_value_error(self, submit_service):
        svc, mock_web3 = submit_service
        with pytest.raises(ValueError, match="Invalid signed transaction hex"):
            svc.submit_sign_request_raw_transaction(
                "not-hex",
                expected_chain_id="137",
                expected_to_address="0x" + "77" * 20,
            )
        mock_web3.eth.send_raw_transaction.assert_not_called()
