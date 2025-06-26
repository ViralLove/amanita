import os
import pytest
from web3 import Web3
from bot.services.core.blockchain import BlockchainService
from web3.middleware import ExtraDataToPOAMiddleware

# Устанавливаем профиль на localhost для теста
os.environ["BLOCKCHAIN_PROFILE"] = "localhost"

# Ожидаемые контракты и их характеристики
EXPECTED_CONTRACTS = {
    "InviteNFT": {
        "name": "Amanita Invite",
        "symbol": "AINV"
    }
    #,
    #"AmanitaSale": {
    #    "name": "Amanita Sale"
    #},
    #"AmanitaToken": {
    #    "name": "Amanita Coin",
    #    "symbol": "AMN"
    #},
    #"OrderNFT": {
    #    "name": "Amanita Order",
    #    "symbol": "ORD"
    #},
    #"ReviewNFT": {
    #    "name": "Amanita Review",
    #    "symbol": "REV"
    #}
}

@pytest.fixture
def blockchain_service():
    """Фикстура для создания экземпляра BlockchainService"""
    # Сбрасываем синглтон перед каждым тестом
    BlockchainService.reset()
    return BlockchainService()

def test_registry_connection(blockchain_service):
    """Тест подключения к реестру контрактов"""
    print("\n=== Тест подключения к реестру ===")
    
    # Проверяем что реестр инициализирован
    assert blockchain_service.registry is not None, "Реестр не инициализирован"
    
    # Проверяем адрес реестра
    registry_address = blockchain_service.registry.address
    assert Web3.is_address(registry_address), f"Невалидный адрес реестра: {registry_address}"
    print(f"✓ Адрес реестра: {registry_address}")
    
    # Проверяем что реестр содержит байткод (является смарт-контрактом)
    code = blockchain_service.web3.eth.get_code(registry_address)
    assert code and code != b'', "Реестр не содержит байткод"
    print(f"✓ Байткод реестра: {len(code)} байт")
    
    # Проверяем доступность методов реестра
    try:
        owner = blockchain_service.registry.functions.owner().call()
        assert Web3.is_address(owner), f"Невалидный адрес владельца реестра: {owner}"
        print(f"✓ Владелец реестра: {owner}")
    except Exception as e:
        pytest.fail(f"Ошибка при вызове метода owner(): {e}")

def test_contract_names(blockchain_service):
    """Тест получения списка контрактов из реестра"""
    print("\n=== Тест списка контрактов ===")
    
    try:
        # Получаем все имена контрактов из реестра
        contract_names = blockchain_service.registry.functions.getAllContractNames().call()
        assert len(contract_names) > 0, "Список контрактов пуст"
        print(f"Найдено контрактов: {len(contract_names)}")
        
        # Проверяем что все ожидаемые контракты присутствуют
        for name in EXPECTED_CONTRACTS:
            assert name in contract_names, f"Контракт {name} отсутствует в реестре"
            print(f"✓ Контракт {name} найден в реестре")
            
        # Выводим все имена для информации
        print("\nСписок всех контрактов в реестре:")
        for name in contract_names:
            print(f"  - {name}")
            
    except Exception as e:
        pytest.fail(f"Ошибка при получении списка контрактов: {e}")

def test_contract_addresses(blockchain_service):
    """Тест получения адресов контрактов из реестра"""
    print("\n=== Тест адресов контрактов ===")
    
    try:
        for name in EXPECTED_CONTRACTS:
            # Получаем адрес из реестра
            address = blockchain_service.registry.functions.getAddress(name).call()
            assert Web3.is_address(address), f"Невалидный адрес для {name}: {address}"
            
            # Проверяем что по адресу есть байткод
            code = blockchain_service.web3.eth.get_code(address)
            assert code and code != b'', f"Контракт {name} не содержит байткод"
            
            print(f"✓ {name}:")
            print(f"  Адрес: {address}")
            print(f"  Байткод: {len(code)} байт")
            
    except Exception as e:
        pytest.fail(f"Ошибка при проверке адресов контрактов: {e}")

def test_contract_initialization(blockchain_service):
    """Тест инициализации контрактов через сервис"""
    print("\n=== Тест инициализации контрактов ===")
    
    for name, meta in EXPECTED_CONTRACTS.items():
        contract = blockchain_service.get_contract(name)
        assert contract is not None, f"Контракт {name} не инициализирован"
        
        print(f"\nПроверка контракта {name}:")
        
        try:
            # Проверяем базовые методы
            if "name" in meta:
                contract_name = blockchain_service.call_contract_function(name, 'name')
                assert contract_name == meta["name"], f"Неверное имя контракта: {contract_name} != {meta['name']}"
                print(f"✓ name: {contract_name}")
            
            if "symbol" in meta:
                symbol = blockchain_service.call_contract_function(name, 'symbol')
                assert symbol == meta["symbol"], f"Неверный символ: {symbol} != {meta['symbol']}"
                print(f"✓ symbol: {symbol}")
                
        except Exception as e:
            pytest.fail(f"Ошибка при проверке методов контракта {name}: {e}")

def test_error_handling(blockchain_service):
    """Тест обработки ошибок"""
    print("\n=== Тест обработки ошибок ===")
    
    # Тест получения несуществующего контракта
    non_existent = blockchain_service.get_contract("NonExistentContract")
    assert non_existent is None, "Должен вернуться None для несуществующего контракта"
    print("✓ Корректная обработка несуществующего контракта")
    
    # Тест вызова функции несуществующего контракта
    result = blockchain_service.call_contract_function("NonExistentContract", "someFunction")
    assert result is None, "Должен вернуться None при вызове функции несуществующего контракта"
    print("✓ Корректная обработка вызова функции несуществующего контракта")
    
    try:
        # Тест получения адреса несуществующего контракта из реестра
        address = blockchain_service.registry.functions.getAddress("NonExistentContract").call()
        assert address == "0x" + "0" * 40, "Должен вернуться нулевой адрес"
        print("✓ Корректная обработка получения адреса несуществующего контракта")
    except Exception as e:
        print(f"! Неожиданное поведение при запросе несуществующего контракта: {e}")

def test_get_all_products(blockchain_service):
    """Тест получения всех продуктов"""
    print("\n=== Тест получения всех продуктов ===")
    products = blockchain_service.get_all_products()
    print(f"Найдено продуктов: {len(products)}")
    for product in products:
        print(f"Продукт: {product}")

def test_network_info(blockchain_service):
    """Проверка информации о сети"""
    print("\n=== Информация о сети ===")
    assert blockchain_service.web3.is_connected(), "Нет подключения к ноде"
    
    print(f"Подключение к: {blockchain_service.web3.provider.endpoint_uri}")
    print(f"Версия клиента: {blockchain_service.web3.client_version}")
    print(f"Chain ID: {blockchain_service.web3.eth.chain_id}")
    print(f"Последний блок: {blockchain_service.web3.eth.block_number}")
    print(f"Gas Price: {blockchain_service.web3.from_wei(blockchain_service.web3.eth.gas_price, 'gwei')} Gwei")

# ==================== ТЕСТЫ МЕТОДОВ КОНТРАКТА ====================

def test_mint_invites_function(blockchain_service):
    """Тест функции mintInvites"""
    print("\n=== Тест mintInvites ===")
    
    # Генерируем тестовый код
    import random
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    first_part = ''.join(random.choice(chars) for _ in range(4))
    second_part = ''.join(random.choice(chars) for _ in range(4))
    test_code = f"AMANITA-{first_part}-{second_part}"
    
    print(f"Тестовый код: {test_code}")
    
    # Проверяем что код не существует
    try:
        token_id = blockchain_service.call_contract_function("InviteNFT", "getTokenIdByInviteCode", test_code)
        print(f"Токен уже существует: {token_id}")
    except Exception as e:
        print(f"Код не существует (ожидаемо): {e}")
    
    # Проверяем что функция доступна
    contract = blockchain_service.get_contract("InviteNFT")
    assert hasattr(contract.functions, 'mintInvites'), "Функция mintInvites не найдена"
    print("✓ Функция mintInvites доступна")

def test_activate_and_mint_invites_function(blockchain_service):
    """Тест функции activateAndMintInvites"""
    print("\n=== Тест activateAndMintInvites ===")
    
    # Проверяем что функция доступна
    contract = blockchain_service.get_contract("InviteNFT")
    assert hasattr(contract.functions, 'activateAndMintInvites'), "Функция activateAndMintInvites не найдена"
    print("✓ Функция activateAndMintInvites доступна")
    
    # Проверяем сигнатуру функции
    function = contract.functions.activateAndMintInvites
    print(f"Сигнатура функции: {function.abi}")
    
    # Проверяем что функция принимает правильные параметры
    # activateAndMintInvites(string memory inviteCode, address user, string[] memory newInviteCodes, uint256 expiry)
    expected_params = ['inviteCode', 'user', 'newInviteCodes', 'expiry']
    print(f"Ожидаемые параметры: {expected_params}")

def test_invite_validation_functions(blockchain_service):
    """Тест функций валидации инвайтов"""
    print("\n=== Тест функций валидации ===")
    
    contract = blockchain_service.get_contract("InviteNFT")
    
    # Проверяем наличие функций валидации
    validation_functions = [
        'validateInviteCode',
        'batchValidateInviteCodes',
        'isUserActivated',
        'getAllActivatedUsers'
    ]
    
    for func_name in validation_functions:
        assert hasattr(contract.functions, func_name), f"Функция {func_name} не найдена"
        print(f"✓ Функция {func_name} доступна")

def test_seller_role_functions(blockchain_service):
    """Тест функций для работы с ролями продавца"""
    print("\n=== Тест функций ролей продавца ===")
    
    contract = blockchain_service.get_contract("InviteNFT")
    
    # Проверяем наличие функций для работы с ролями
    role_functions = [
        'isSeller',
        'addSeller',
        'removeSeller'
    ]
    
    for func_name in role_functions:
        assert hasattr(contract.functions, func_name), f"Функция {func_name} не найдена"
        print(f"✓ Функция {func_name} доступна")

def test_invite_metadata_functions(blockchain_service):
    """Тест функций для работы с метаданными инвайтов"""
    print("\n=== Тест функций метаданных ===")
    
    contract = blockchain_service.get_contract("InviteNFT")
    
    # Проверяем наличие функций для работы с метаданными
    metadata_functions = [
        'getInviteExpiry',
        'getInviteTransferHistory',
        'getUserInvites',
        'userInviteCount',
        'totalInvitesMinted',
        'totalInvitesUsed'
    ]
    
    for func_name in metadata_functions:
        assert hasattr(contract.functions, func_name), f"Функция {func_name} не найдена"
        print(f"✓ Функция {func_name} доступна")

if __name__ == "__main__":
    # Создаем сервис
    service = BlockchainService()
    
    # Запускаем все тесты
    test_registry_connection(service)
    test_contract_names(service)
    test_contract_addresses(service)
    test_contract_initialization(service)
    test_error_handling(service)
    test_get_all_products(service)
    test_network_info(service) 
    test_mint_invites_function(service)
    test_activate_and_mint_invites_function(service)
    test_invite_validation_functions(service)
    test_seller_role_functions(service)
    test_invite_metadata_functions(service) 