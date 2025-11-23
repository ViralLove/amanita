from typing import Dict, Tuple, Optional


class _CallWrapper:
    def __init__(self, fn):
        self._fn = fn

    def call(self):
        return self._fn()


class _TxWrapper:
    def __init__(self, fn):
        self._fn = fn

    def transact(self, *args, **kwargs):
        return self._fn()


class AmanitaInternationalContractStub:
    """
    Простейший stub контракта AmanitaInternational.
    Хранит CID'ы в памяти по ключу (entity_type, entity_id, field, lang).
    Имплементирует web3-подобный интерфейс: contract.functions.METHOD(...).call()/transact()
    """

    def __init__(self):
        self._storage: Dict[Tuple[str, str, str, str], str] = {}  # For simple fields
        self._complex_storage: Dict[Tuple[str, str], str] = {}  # For complex fields: (className, language) -> CID
        self.get_cid_calls: int = 0
        self.set_cid_calls: int = 0
        self.get_complex_cid_calls: int = 0
        self.set_complex_cid_calls: int = 0
        self.functions = self.Functions(self, self._storage, self._complex_storage)

    class Functions:
        def __init__(self, parent: "AmanitaInternationalContractStub", storage: Dict[Tuple[str, str, str, str], str], complex_storage: Dict[Tuple[str, str], str]):
            self._parent = parent
            self._storage = storage
            self._complex_storage = complex_storage

        def getSimpleFieldCID(self, entity_type: str, entity_id: str, field: str, lang: str):
            def _do():
                self._parent.get_cid_calls += 1
                return self._storage.get((entity_type, entity_id, field, lang), None)

            return _CallWrapper(_do)

        def setSimpleFieldCID(self, entity_type: str, entity_id: str, field: str, lang: str, cid: str):
            def _do():
                self._parent.set_cid_calls += 1
                self._storage[(entity_type, entity_id, field, lang)] = cid
                return True

            return _TxWrapper(_do)
        
        def getComplexFieldCID(self, className: str, language: str):
            def _do():
                self._parent.get_complex_cid_calls += 1
                return self._complex_storage.get((className, language), "")
            
            return _CallWrapper(_do)
        
        def setComplexFieldCID(self, className: str, language: str, cid: str):
            def _do():
                self._parent.set_complex_cid_calls += 1
                self._complex_storage[(className, language)] = cid
                return True
            
            return _TxWrapper(_do)

    # Удобные методы-индикаторы доступны как поля get_cid_calls/set_cid_calls


class BlockchainServiceStub:
    """
    Stub BlockchainService с методом get_contract(name) → контракт-стаб.
    """

    def __init__(self):
        self._contracts = {
            "AmanitaInternational": AmanitaInternationalContractStub()
        }

    def get_contract(self, name: str):
        return self._contracts.get(name)


