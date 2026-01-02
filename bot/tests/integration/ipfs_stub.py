import hashlib
import json
from typing import Any, Dict, Optional


class InMemoryIPFSService:
    """
    Простой IPFS-стаб с in-memory хранилищем.
    - upload_json(payload) -> cid
    - download_json(cid) -> payload
    """
    def __init__(self, storage: Optional[Dict[str, Any]] = None):
        self._storage: Dict[str, Any] = storage if storage is not None else {}
        self.upload_calls: int = 0
        self.download_calls: int = 0

    @staticmethod
    def _base58_encode(data: bytes) -> str:
        """
        Minimal base58btc encoder (Bitcoin alphabet).
        Needed only to generate deterministic, validate_ipfs_cid()-compatible stub CIDs.
        """
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        n = int.from_bytes(data, "big")
        if n == 0:
            return "1"
        chars = []
        while n > 0:
            n, rem = divmod(n, 58)
            chars.append(alphabet[rem])
        # preserve leading zeros as '1'
        pad = 0
        for b in data:
            if b == 0:
                pad += 1
            else:
                break
        return ("1" * pad) + "".join(reversed(chars))

    @classmethod
    def _make_valid_qm_cid(cls, payload: Any) -> str:
        """
        Generate a deterministic fake CIDv0-like string that passes ProductStorageService.validate_ipfs_cid().

        IMPORTANT:
        - This is NOT a real CID/multihash.
        - It is only a test stub identifier with shape: 'Qm' + 44 base58 chars (len=46).
        """
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha256(blob).digest()
        suffix = cls._base58_encode(digest)
        # normalize length to exactly 44 base58 chars
        if len(suffix) < 44:
            suffix = (suffix + ("1" * 44))[:44]
        else:
            suffix = suffix[:44]
        return f"Qm{suffix}"

    def upload_json(self, payload: Any) -> str:
        # Стаб: CID должен проходить ProductStorageService.validate_ipfs_cid()
        # (иначе после перевода MultilingualIPFSService на ProductStorageService тесты станут ложно-красными).
        cid = self._make_valid_qm_cid(payload)
        self._storage[cid] = payload
        self.upload_calls += 1
        return cid

    def download_json(self, cid: str) -> Optional[Any]:
        self.download_calls += 1
        return self._storage.get(cid)


class IPFSFactoryStub:
    """
    Фабрика, совместимая с ожидаемым интерфейсом ipfs_factory.get_service().
    В каждый тест можно прокидывать отдельный storage для изоляции.
    """
    def __init__(self, storage: Optional[Dict[str, Any]] = None):
        self._service = InMemoryIPFSService(storage=storage)

    def get_service(self) -> InMemoryIPFSService:
        return self._service


