from supabase import create_client, Client
from typing import Optional, List
import os
from bot.models.product import Product

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


    # TODO:
    # - create_product()
    # - sync_catalog_entry()
    # - cart management if needed
