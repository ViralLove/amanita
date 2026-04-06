"""SSOT CHAIN_ID / CHAIN_ID_INT в bot/config (ASG-4)."""

import importlib
import sys


def test_config_chain_id_default_137_when_env_unset(monkeypatch):
    """
    Нет CHAIN_ID в os.environ и подмешивание .env отключено → дефолт 137.
    (Патч load_dotenv нужен, иначе из .env подтянется реальный CHAIN_ID и тест перестанет быть про дефолт.)
    """
    monkeypatch.delenv("CHAIN_ID", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    if "config" in sys.modules:
        del sys.modules["config"]
    import config as cfg

    importlib.reload(cfg)
    assert cfg.CHAIN_ID == "137"
    assert cfg.CHAIN_ID_INT == 137


def test_config_chain_id_from_env(monkeypatch):
    monkeypatch.setenv("CHAIN_ID", "31337")
    if "config" in sys.modules:
        del sys.modules["config"]
    import config as cfg

    importlib.reload(cfg)
    assert cfg.CHAIN_ID == "31337"
    assert cfg.CHAIN_ID_INT == 31337
