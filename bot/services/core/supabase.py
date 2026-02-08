from supabase import create_client, Client
from typing import Any, Dict, List, Optional
import os
from datetime import datetime, timezone
from model.product import Product

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class SupabaseService:
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # --- Orders ---

    def create_order(self, order_data: dict) -> dict:
        """Insert a new order row into the orders table."""
        response = self.client.table("orders").insert(order_data).execute()
        return response.data[0] if response.data else {}

    def update_order_status(self, order_hash: str, status: str) -> bool:
        """Update the status of an order given its order_hash."""
        response = self.client.table("orders").update({"status": status}).eq("order_hash", order_hash).execute()
        return response.status_code == 200

    def get_order_by_hash(self, order_hash: str) -> Optional[dict]:
        """Fetch order details by order_hash."""
        response = self.client.table("orders").select("*").eq("order_hash", order_hash).limit(1).execute()
        return response.data[0] if response.data else None

    def get_orders_by_seller(self, seller_address: str, status: Optional[str] = None) -> List[dict]:
        """Fetch orders for a given seller, optionally filtered by status."""
        query = self.client.table("orders").select("*").eq("seller_address", seller_address)
        if status:
            query = query.eq("status", status)
        response = query.execute()
        return response.data or []

    # --- OTP Handling ---

    def store_otp(self, order_id: str, otp: int, otp_amount: float) -> bool:
        """Update OTP and final amount for an existing order."""
        response = self.client.table("orders").update({
            "otp": otp,
            "otp_amount": otp_amount
        }).eq("id", order_id).execute()
        return response.status_code == 200

    def get_order_by_otp_amount(self, amount: float) -> Optional[dict]:
        """Search for an order using a known OTP-modified amount."""
        response = self.client.table("orders").select("*").eq("otp_amount", amount).limit(1).execute()
        return response.data[0] if response.data else None

    # --- Shipping (optional) ---

    def get_shipping_options_for_seller(self, seller_address: str) -> List[dict]:
        response = self.client.table("shipping_methods").select("*").eq("seller_address", seller_address).execute()
        return response.data or []

    def add_shipping_option(self, shipping_data: dict) -> dict:
        response = self.client.table("shipping_methods").insert(shipping_data).execute()
        return response.data[0] if response.data else {}

    # --- Product Catalog ---

    async def sync_products(self, products: List[Product]) -> None:
        """
        Сохраняет или обновляет продукты и описания в Supabase.
        """
        for product in products:
            # --- 1. Upsert Product Description ---
            desc = product.description
            self.client.table("product_descriptions").upsert({
                "id": product.description_cid,
                "title": desc.title,
                "scientific_name": desc.scientific_name,
                "generic_description": desc.generic_description,
                "effects": desc.effects,
                "shamanic": desc.shamanic,
                "warnings": desc.warnings
            }).execute()

            # --- 2. Upsert Dosage Instructions ---
            if desc.dosage:
                # Удалим предыдущие (если есть)
                self.client.table("dosage_instructions").delete().eq("description_id", product.description_cid).execute()

                for instruction in desc.dosage:
                    self.client.table("dosage_instructions").insert({
                        "description_id": product.description_cid,
                        "type": instruction.type,
                        "title": instruction.title,
                        "description": instruction.description
                    }).execute()

            # --- 3. Upsert Product ---
            self.client.table("products").upsert({
                "id": product.id,
                "alias": product.alias,
                "status": product.status,
                "cid": product.cid,
                "title": product.title,
                "description_cid": product.description_cid,
                "cover_image_url": product.cover_image_url,
                "categories": product.categories,
                "forms": product.forms,
                "species": product.species
            }).execute()

            # --- 4. Upsert Prices ---
            self.client.table("product_prices").delete().eq("product_id", product.id).execute()
            for p in product.prices:
                self.client.table("product_prices").insert({
                    "product_id": product.id,
                    "price": p.price,
                    "currency": p.currency,
                    "weight": p.weight,
                    "weight_unit": p.weight_unit,
                    "volume": p.volume,
                    "volume_unit": p.volume_unit,
                    "form": p.form
                }).execute()


    # --- Uploads (Arweave data upload flow, task 3.2) ---

    def insert_upload(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a row into uploads table. Returns the inserted row (with upload_id if generated)."""
        response = self.client.table("uploads").insert(row).execute()
        return response.data[0] if response.data else {}

    def get_upload_by_id(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Fetch one upload by upload_id."""
        response = self.client.table("uploads").select("*").eq("upload_id", upload_id).limit(1).execute()
        return response.data[0] if response.data else None

    def update_upload_status(
        self,
        upload_id: str,
        status: str,
        failure_reason: Optional[str] = None,
        failure_code: Optional[str] = None,
    ) -> bool:
        """Update status (and optional failure_reason, failure_code) for an upload."""
        payload: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if failure_reason is not None:
            payload["failure_reason"] = failure_reason
        if failure_code is not None:
            payload["failure_code"] = failure_code
        response = self.client.table("uploads").update(payload).eq("upload_id", upload_id).execute()
        return bool(response.data)

    def update_upload_callback(
        self,
        upload_id: str,
        item_id: str,
        bundle_tx_id: str,
        owner_address: Optional[str] = None,
    ) -> bool:
        """Set published state: status=published, item_id, bundle_tx_id, owner_address."""
        payload: Dict[str, Any] = {
            "status": "published",
            "item_id": item_id,
            "bundle_tx_id": bundle_tx_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if owner_address is not None:
            payload["owner_address"] = owner_address
        response = self.client.table("uploads").update(payload).eq("upload_id", upload_id).execute()
        return bool(response.data)

    def list_uploads_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List uploads with given status (e.g. for finalizer: status=published)."""
        response = self.client.table("uploads").select("*").eq("status", status).limit(limit).execute()
        return response.data or []

    def count_uploads_by_user_since(self, user_id: str, since_ts: str) -> int:
        """Count uploads for user with created_at >= since_ts (for rate limit per minute)."""
        response = (
            self.client.table("uploads")
            .select("upload_id")
            .eq("user_id", user_id)
            .gte("created_at", since_ts)
            .execute()
        )
        return len(response.data) if response.data else 0

    def sum_payload_size_by_user_since(self, user_id: str, since_ts: str) -> int:
        """Sum payload_size for user with created_at >= since_ts (for rate limit bytes per day)."""
        response = (
            self.client.table("uploads")
            .select("payload_size")
            .eq("user_id", user_id)
            .gte("created_at", since_ts)
            .execute()
        )
        total = 0
        for row in response.data or []:
            total += row.get("payload_size") or 0
        return total

    # TODO:
    # - create_product()
    # - sync_catalog_entry()
    # - cart management if needed
