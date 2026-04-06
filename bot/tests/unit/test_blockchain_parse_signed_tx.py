"""Проверка разбора chain_id и `to` из raw (typed + legacy) для submit_sign_request."""

from hexbytes import HexBytes
from web3 import Web3

from services.core.blockchain import _parse_signed_transaction_chain_and_to


def test_parse_type2_signed_tx():
    w3 = Web3()
    acct = w3.eth.account.create()
    tx = {
        "chainId": 137,
        "gas": 21000,
        "maxFeePerGas": w3.to_wei(2, "gwei"),
        "maxPriorityFeePerGas": w3.to_wei(1, "gwei"),
        "nonce": 0,
        "to": "0x" + "33" * 20,
        "value": 0,
        "type": 2,
        "data": b"",
    }
    signed = w3.eth.account.sign_transaction(tx, acct.key)
    raw = signed.raw_transaction
    chain_id, to_addr = _parse_signed_transaction_chain_and_to(bytes(HexBytes(raw)))
    assert chain_id == 137
    assert to_addr == Web3.to_checksum_address("0x" + "33" * 20)


def test_parse_legacy_eip155_signed_tx():
    w3 = Web3()
    acct = w3.eth.account.create()
    tx = {
        "chainId": 137,
        "gas": 21000,
        "gasPrice": w3.to_wei(1, "gwei"),
        "nonce": 0,
        "to": "0x" + "44" * 20,
        "value": 0,
    }
    signed = w3.eth.account.sign_transaction(tx, acct.key)
    raw = signed.raw_transaction
    chain_id, to_addr = _parse_signed_transaction_chain_and_to(bytes(HexBytes(raw)))
    assert chain_id == 137
    assert to_addr == Web3.to_checksum_address("0x" + "44" * 20)
