dotenv.load_dotenv()
logger = logging.getLogger(__name__)

PRODUCT_KEY_ID = "id"
PRODUCT_KEY_IPFS_CID = "ipfsCID"
PRODUCT_KEY_ACTIVE = "active"

SELLER_PRIVATE_KEY = os.getenv("SELLER_PRIVATE_KEY")

class OrderManagementService:
    """
    Сервис для управления заказами.
    """

    def __init__(self):
        pass

    def get_order(self, order_id: str) -> Optional[Order]:
        pass

    def create_order(
        buyer_address: str,
        seller_address: str,
        cart: list[dict],
        shipping_option: dict,
        destination_country: str,
        delivery_address: str,
        comment: str = ""
    ) -> dict:
        """
        1. Расчёт суммы
        2. Генерация OTP
        3. Хранение IPFS-версии заказа
        4. Создание записи в Supabase
        5. Вызов Orders.sol → createOrder(...)
        """
        pass  # TODO реализовать каждый шаг

    def generate_otp(base_amount: float) -> (float, str):
        """
        Добавляет 4-6 значений в decimal часть суммы для OTP.
        Возвращает сумму и OTP как строку.
        """
        pass  # TODO: использовать random + hash

    def get_orders_for_seller(seller_address: str, status: str = None) -> list[dict]:
        """
        Фильтрация заказов по селлеру и статусу.
        """
        pass

    def get_order_by_otp(otp: str) -> Optional[dict]:
        """
        Возвращает заказ по OTP.
        """
        pass

    def listen_for_payments(self):
        # web3 loop
        # on event:
        #   parse amount → extract OTP
        #   lookup in supabase
        #   mark paid
        #   trigger update
        pass


