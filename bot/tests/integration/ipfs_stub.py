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

    def upload_json(self, payload: Any) -> str:
        # Стаб: CID = cid://<sha1(JSON)>
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        digest = hashlib.sha1(blob).hexdigest()
        cid = f"cid://{digest}"
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


