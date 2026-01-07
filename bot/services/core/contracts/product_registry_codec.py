from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence


class ProductRegistryCodecError(Exception):
    """Raised when the on-chain ProductRegistry.getProduct() result doesn't match expected ABI shape."""


@dataclass(frozen=True)
class ProductRegistryGetProduct:
    """
    Typed representation of ProductRegistryLogic.getProduct() return value:
      (id, seller, businessId, componentIds, metadataCID, active)
    """

    id: int
    seller: str
    business_id: str
    component_ids: list[str]
    metadata_cid: str
    active: bool


def _as_str_address(value: Any) -> str:
    # Web3.py typically returns checksum address as str already.
    if isinstance(value, str):
        return value
    # Sometimes it can be HexBytes/bytes.
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    return str(value)


def _as_str_list(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (list, tuple)):
        return [str(v) for v in values]
    # Unexpected: keep diagnostic value but still return list for safety in logs.
    return [str(values)]


def decode_get_product_tuple(raw: Any, *, allow_legacy: bool = False) -> ProductRegistryGetProduct:
    """
    Decode raw tuple returned by Web3 contract call ProductRegistry.getProduct(...).

    Default (strict) mode expects UUPS ProductRegistryLogic ABI:
      len == 6: (id, seller, businessId, componentIds, metadataCID, active)

    Optional legacy mode supports old non-UUPS ProductRegistry.sol ABI:
      len == 4: (id, seller, ipfsCID, active)

    Raises:
        ProductRegistryCodecError: if shape is unexpected / unsafe to interpret.
    """

    if raw is None:
        raise ProductRegistryCodecError("getProduct returned None")

    if not hasattr(raw, "__len__") or not hasattr(raw, "__getitem__"):
        raise ProductRegistryCodecError(f"getProduct returned non-sequence: {type(raw).__name__}: {raw!r}")

    length = len(raw)  # type: ignore[arg-type]

    if length == 6:
        product_id = int(raw[0])
        seller = _as_str_address(raw[1])
        business_id = str(raw[2])
        component_ids = _as_str_list(raw[3])
        metadata_cid = str(raw[4])
        active = bool(raw[5])

        if product_id <= 0:
            raise ProductRegistryCodecError(f"Invalid product id decoded: {product_id} from {raw!r}")

        return ProductRegistryGetProduct(
            id=product_id,
            seller=seller,
            business_id=business_id,
            component_ids=component_ids,
            metadata_cid=metadata_cid,
            active=active,
        )

    if allow_legacy and length == 4:
        product_id = int(raw[0])
        seller = _as_str_address(raw[1])
        ipfs_cid = str(raw[2])
        active = bool(raw[3])

        if product_id <= 0:
            raise ProductRegistryCodecError(f"Invalid legacy product id decoded: {product_id} from {raw!r}")

        return ProductRegistryGetProduct(
            id=product_id,
            seller=seller,
            business_id="",
            component_ids=[],
            metadata_cid=ipfs_cid,
            active=active,
        )

    raise ProductRegistryCodecError(
        f"Unexpected getProduct() tuple length={length} (allow_legacy={allow_legacy}). raw={raw!r}"
    )


