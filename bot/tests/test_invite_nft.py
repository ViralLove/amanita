import pytest
from web3 import Web3
from bot.tests.utils.invite_code_generator import generate_invite_code, validate_invite_code
import os

def test_onboarding_success(web3, invite_nft_contract, seller_account, user_account):
    """Тест успешного онбординга"""
    # Генерируем 12 уникальных инвайт-кодов
    invite_codes = [generate_invite_code(prefix="test") for _ in range(12)]
    for code in invite_codes:
        assert validate_invite_code(code), "Сгенерированный код невалидный"
    
    # Минтим 12 инвайтов
    tx_hash = invite_nft_contract.functions.mintInvites(
        invite_codes,
        0
    ).transact({'from': seller_account.address})
    
    # Проверяем что код уникальный
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.mintInvites(
            invite_codes,
            0
        ).transact({'from': seller_account.address})
    assert "Invite code already exists" in str(exc_info.value)

def test_seller_can_mint_any_batch_size(web3, invite_nft_contract, seller_account):
    """
    Селлер может минтить себе batch любого размера (1, 12, 100), сколько угодно раз.
    Проверяем, что owner всех инвайтов — seller_account.
    """
    # Минтим 1 инвайт
    codes1 = [generate_invite_code(prefix="one")] 
    tx_hash1 = invite_nft_contract.functions.mintInvites(codes1, 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash1)
    token_id1 = invite_nft_contract.functions.getTokenIdByInviteCode(codes1[0]).call()
    assert invite_nft_contract.functions.ownerOf(token_id1).call() == seller_account.address

    # Минтим 12 инвайтов
    codes12 = [generate_invite_code(prefix="dozen") for _ in range(12)]
    tx_hash12 = invite_nft_contract.functions.mintInvites(codes12, 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash12)
    for code in codes12:
        token_id = invite_nft_contract.functions.getTokenIdByInviteCode(code).call()
        assert invite_nft_contract.functions.ownerOf(token_id).call() == seller_account.address

    # Минтим 100 инвайтов
    codes100 = [generate_invite_code(prefix="hundred") for _ in range(100)]
    tx_hash100 = invite_nft_contract.functions.mintInvites(codes100, 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash100)
    for code in codes100:
        token_id = invite_nft_contract.functions.getTokenIdByInviteCode(code).call()
        assert invite_nft_contract.functions.ownerOf(token_id).call() == seller_account.address

def test_invite_code_uniqueness_new(web3, invite_nft_contract, seller_account):
    """
    Нельзя минтить один и тот же inviteCode дважды, даже в разных batch-ах.
    """
    code = generate_invite_code(prefix="uniq")
    invite_nft_contract.functions.mintInvites([code], 0).transact({'from': seller_account.address})
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.mintInvites([code], 0).transact({'from': seller_account.address})
    assert "Invite code already exists" in str(exc_info.value)

def test_unauthorized_mint_new(web3, invite_nft_contract, user_account):
    """
    Не-seller не может минтить инвайты (mintInvites).
    """
    code = generate_invite_code(prefix="unauth")
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.mintInvites([code], 0).transact({'from': user_account.address})
    assert "AccessControlUnauthorizedAccount" in str(exc_info.value)

def test_activation_and_new_invites(web3, invite_nft_contract, seller_account):
    """
    Селлер минтит себе инвайт, пользователь активирует его и получает 12 новых инвайтов.
    """
    # Селлер минтит себе 1 инвайт
    code = generate_invite_code(prefix="act1")
    invite_nft_contract.functions.mintInvites([code], 0).transact({'from': seller_account.address})
    # Новый пользователь
    user = web3.eth.account.create()
    # Генерируем 12 новых инвайтов для user
    new_codes = [generate_invite_code(prefix="user12") for _ in range(12)]
    # Активация и минтинг
    tx_hash = invite_nft_contract.functions.activateAndMintInvites(
        code, user.address, new_codes, 0
    ).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    # Проверяем, что все новые инвайты принадлежат user
    for c in new_codes:
        token_id = invite_nft_contract.functions.getTokenIdByInviteCode(c).call()
        assert invite_nft_contract.functions.ownerOf(token_id).call() == user.address
    # Повторная активация — ошибка
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.activateAndMintInvites(
            code, user.address, new_codes, 0
        ).transact({'from': seller_account.address})
    assert "already_used" in str(exc_info.value) or "already activated" in str(exc_info.value)

def test_batch_invites_minted_event(web3, invite_nft_contract, seller_account):
    """
    Проверяем событие BatchInvitesMinted: owner — seller_account, inviteCodes совпадают.
    """
    codes = [generate_invite_code(prefix="event") for _ in range(5)]
    tx_hash = invite_nft_contract.functions.mintInvites(codes, 0).transact({'from': seller_account.address})
    receipt = web3.eth.get_transaction_receipt(tx_hash)
    events = invite_nft_contract.events.BatchInvitesMinted().process_receipt(receipt)
    assert len(events) == 1
    event = events[0]['args']
    assert event['to'] == seller_account.address
    assert set(event['inviteCodes']) == set(codes)

def test_batch_with_duplicates_reverts(web3, invite_nft_contract, seller_account):
    """
    Минтинг batch с дублирующимися inviteCode — revert.
    """
    code = generate_invite_code(prefix="dup")
    codes = [code, code]
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.mintInvites(codes, 0).transact({'from': seller_account.address})
    assert "Duplicate inviteCode in batch" in str(exc_info.value)

def test_activate_and_mint_requires_12_invites(web3, invite_nft_contract, seller_account):
    """
    activateAndMintInvites должен минтить ровно 12 новых инвайтов, иначе revert.
    Если тест не падает — требуется доработка require в контракте.
    """
    # Селлер минтит себе инвайт
    code = generate_invite_code(prefix="act12")
    invite_nft_contract.functions.mintInvites([code], 0).transact({'from': seller_account.address})
    user = web3.eth.account.create()
    # Меньше 12 — ошибка
    codes11 = [generate_invite_code(prefix="less") for _ in range(11)]
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.activateAndMintInvites(
            code, user.address, codes11, 0
        ).transact({'from': seller_account.address})
    # Если здесь не выбрасывается ошибка — в контракте нет require на 12 инвайтов!
    assert "Must mint exactly 12 invites" in str(exc_info.value)
    # Больше 12 — ошибка
    codes13 = [generate_invite_code(prefix="more") for _ in range(13)]
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.activateAndMintInvites(
            code, user.address, codes13, 0
        ).transact({'from': seller_account.address})
    assert "Must mint exactly 12 invites" in str(exc_info.value)
    # Ровно 12 — проходит
    codes12 = [generate_invite_code(prefix="ok12") for _ in range(12)]
    tx_hash = invite_nft_contract.functions.activateAndMintInvites(
        code, user.address, codes12, 0
    ).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    for c in codes12:
        token_id = invite_nft_contract.functions.getTokenIdByInviteCode(c).call()
        assert invite_nft_contract.functions.ownerOf(token_id).call() == user.address

def test_activation_of_nonexistent_code_reverts_new(web3, invite_nft_contract, seller_account):
    """
    Попытка активировать несуществующий inviteCode — revert.
    """
    user = web3.eth.account.create()
    fake_code = "not_exist_" + os.urandom(4).hex()
    codes = [generate_invite_code(prefix="new") for _ in range(12)]
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.activateAndMintInvites(
            fake_code, user.address, codes, 0
        ).transact({'from': seller_account.address})
    assert "not_found" in str(exc_info.value) or "Invite does not exist" in str(exc_info.value)

def test_contract_metadata(web3, invite_nft_contract):
    """Проверка базовых метаданных контракта"""
    assert invite_nft_contract.functions.name().call() == "Amanita Invite"
    assert invite_nft_contract.functions.symbol().call() == "AINV"  # Обновлено с INV на AINV

def test_soulbound_mechanism(web3, invite_nft_contract, seller_account, user_account):
    """
    Тест механизма Soulbound Token:
    - Можно минтить (from == address(0))
    - Можно сжигать (to == address(0))
    - Нельзя передавать между адресами
    """
    # Минтим инвайт
    code = generate_invite_code(prefix="soul")
    tx_hash = invite_nft_contract.functions.mintInvites([code], 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    token_id = invite_nft_contract.functions.getTokenIdByInviteCode(code).call()
    
    # Проверяем что токен принадлежит seller_account
    assert invite_nft_contract.functions.ownerOf(token_id).call() == seller_account.address
    
    # Пытаемся передать токен - должно быть отклонено
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.transferFrom(
            seller_account.address,
            user_account.address,
            token_id
        ).transact({'from': seller_account.address})
    assert "soulbound" in str(exc_info.value).lower()
    
    # Проверяем safeTransferFrom - тоже должно быть отклонено
    with pytest.raises(Exception) as exc_info:
        invite_nft_contract.functions.safeTransferFrom(
            seller_account.address,
            user_account.address,
            token_id
        ).transact({'from': seller_account.address})
    assert "soulbound" in str(exc_info.value).lower()

def test_registry_integration(web3, invite_nft_contract, registry_contract):
    """Проверка интеграции с реестром"""
    # Проверяем что контракт зарегистрирован
    invite_address = registry_contract.functions.getAddress("InviteNFT").call()
    assert invite_address == invite_nft_contract.address, "Адрес в реестре не соответствует адресу контракта"
    
    # Проверяем что это действительно тот же контракт
    registered_contract = web3.eth.contract(
        address=invite_address,
        abi=invite_nft_contract.abi
    )
    assert registered_contract.functions.name().call() == "Amanita Invite"
    assert registered_contract.functions.symbol().call() == "AINV"

def test_invite_transfer_history(web3, invite_nft_contract, seller_account, user_account):
    """
    Проверка истории владения инвайтом:
    - История должна включать первого владельца
    - История должна обновляться при активации
    """
    # Минтим инвайт
    code = generate_invite_code(prefix="hist")
    tx_hash = invite_nft_contract.functions.mintInvites([code], 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    token_id = invite_nft_contract.functions.getTokenIdByInviteCode(code).call()
    
    # Проверяем историю после минта
    history = invite_nft_contract.functions.getInviteTransferHistory(token_id).call()
    assert len(history) == 1, "История должна содержать одну запись после минта"
    assert history[0] == seller_account.address, "Первая запись должна быть адресом seller_account"
    
    # Активируем инвайт для пользователя
    new_codes = [generate_invite_code(prefix="hist_new") for _ in range(12)]
    tx_hash = invite_nft_contract.functions.activateAndMintInvites(
        code, user_account.address, new_codes, 0
    ).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Проверяем обновленную историю
    history = invite_nft_contract.functions.getInviteTransferHistory(token_id).call()
    assert len(history) == 2, "История должна содержать две записи после активации"
    assert history[0] == seller_account.address, "Первая запись должна быть адресом seller_account"
    assert history[1] == user_account.address, "Вторая запись должна быть адресом user_account"

def test_invite_expiry(web3, invite_nft_contract, seller_account):
    """
    Проверка механизма истечения срока действия инвайтов:
    - Создание с expiry
    - Проверка валидности до истечения
    - Проверка невалидности после истечения
    """
    # Текущий timestamp
    current_time = web3.eth.get_block('latest').timestamp
    expiry_time = current_time + 3600  # +1 час
    
    # Минтим инвайт с expiry
    code = generate_invite_code(prefix="exp")
    tx_hash = invite_nft_contract.functions.mintInvites([code], expiry_time).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    token_id = invite_nft_contract.functions.getTokenIdByInviteCode(code).call()
    
    # Проверяем что expiry установлен правильно
    assert invite_nft_contract.functions.getInviteExpiry(token_id).call() == expiry_time
    
    # Проверяем валидность инвайта
    valid, reason = invite_nft_contract.functions.validateInviteCode(code).call()
    assert valid, f"Инвайт должен быть валидным до истечения срока, причина: {reason}"
    
    # Увеличиваем время в блокчейне на 2 часа (чтобы инвайт истек)
    # В Ganache можно использовать evm_increaseTime
    web3.provider.make_request("evm_increaseTime", [7200])  # +2 часа
    web3.provider.make_request("evm_mine", [])  # Майним новый блок
    
    # Проверяем что инвайт стал невалидным
    valid, reason = invite_nft_contract.functions.validateInviteCode(code).call()
    assert not valid, "Истекший инвайт должен быть невалидным"
    assert reason == "expired", f"Неверная причина невалидности: {reason}"

def test_batch_validate_invite_codes(web3, invite_nft_contract, seller_account, user_account):
    """
    Проверка batch-валидации инвайт-кодов:
    - Валидные коды
    - Невалидные коды
    - Смешанный набор
    """
    # Создаем набор инвайтов
    valid_codes = [generate_invite_code(prefix="batch_valid") for _ in range(3)]
    invalid_codes = [generate_invite_code(prefix="batch_invalid") for _ in range(2)]
    
    # Минтим валидные инвайты: часть без expiry, часть с будущим expiry
    current_time = web3.eth.get_block('latest').timestamp
    future_time = current_time + 3600
    
    # Минтим инвайты без expiry
    tx_hash = invite_nft_contract.functions.mintInvites(valid_codes[:2], 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Минтим инвайт с будущим expiry
    tx_hash = invite_nft_contract.functions.mintInvites([valid_codes[2]], future_time).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Увеличиваем время в блокчейне на 2 часа
    web3.provider.make_request("evm_increaseTime", [7200])
    web3.provider.make_request("evm_mine", [])
    
    # Проверяем batch-валидацию
    all_codes = valid_codes[:2] + invalid_codes + [valid_codes[2]]
    success, reasons = invite_nft_contract.functions.batchValidateInviteCodes(all_codes, user_account.address).call()
    
    assert len(success) == len(all_codes), "Количество результатов не соответствует количеству кодов"
    assert len(reasons) == len(all_codes), "Количество причин не соответствует количеству кодов"
    
    # Проверяем результаты для валидных кодов без expiry
    for i in range(2):
        assert success[i], f"Валидный код {valid_codes[i]} помечен как невалидный"
        assert reasons[i] == "", f"Для валидного кода указана причина: {reasons[i]}"
    
    # Проверяем результаты для невалидных кодов
    for i in range(2, 4):
        assert not success[i], f"Невалидный код помечен как валидный"
        assert reasons[i] == "not_found", f"Неверная причина для несуществующего кода: {reasons[i]}"
    
    # Проверяем результат для истекшего кода
    assert not success[-1], "Истекший код помечен как валидный"
    assert reasons[-1] == "expired", f"Неверная причина для истекшего кода: {reasons[-1]}"

def test_invite_counters(web3, invite_nft_contract, seller_account, user_account):
    """
    Проверка счетчиков инвайтов:
    - totalInvitesMinted увеличивается при минте
    - totalInvitesUsed увеличивается при активации
    """
    # Запоминаем начальные значения
    initial_minted = invite_nft_contract.functions.totalInvitesMinted().call()
    initial_used = invite_nft_contract.functions.totalInvitesUsed().call()
    
    # Минтим 3 инвайта
    codes = [generate_invite_code(prefix="counter") for _ in range(3)]
    tx_hash = invite_nft_contract.functions.mintInvites(codes, 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Проверяем увеличение totalInvitesMinted
    assert invite_nft_contract.functions.totalInvitesMinted().call() == initial_minted + 3, \
        "totalInvitesMinted не увеличился после минта"
    
    # Активируем один инвайт
    new_codes = [generate_invite_code(prefix="counter_new") for _ in range(12)]
    tx_hash = invite_nft_contract.functions.activateAndMintInvites(
        codes[0], user_account.address, new_codes, 0
    ).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Проверяем увеличение обоих счетчиков
    assert invite_nft_contract.functions.totalInvitesMinted().call() == initial_minted + 15, \
        "totalInvitesMinted не увеличился после активации"
    assert invite_nft_contract.functions.totalInvitesUsed().call() == initial_used + 1, \
        "totalInvitesUsed не увеличился после активации"

def test_activated_users_tracking(web3, invite_nft_contract, seller_account, user_accounts):
    """
    Проверка отслеживания активированных пользователей:
    - Пользователь добавляется в список после активации
    - Список корректно возвращает всех активированных пользователей
    """
    # Минтим инвайты для активации
    codes = [generate_invite_code(prefix=f"act_user_{i}") for i in range(3)]
    tx_hash = invite_nft_contract.functions.mintInvites(codes, 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Активируем инвайты для разных пользователей
    activated_users = []
    for i in range(3):
        user = user_accounts[i]
        new_codes = [generate_invite_code(prefix=f"new_user_{i}_{j}") for j in range(12)]
        tx_hash = invite_nft_contract.functions.activateAndMintInvites(
            codes[i], user.address, new_codes, 0
        ).transact({'from': seller_account.address})
        web3.eth.wait_for_transaction_receipt(tx_hash)
        activated_users.append(user.address)
        
        # Проверяем что пользователь активирован
        assert invite_nft_contract.functions.isUserActivated(user.address).call(), \
            f"Пользователь {user.address} не отмечен как активированный"
    
    # Проверяем список всех активированных пользователей
    all_activated = invite_nft_contract.functions.getAllActivatedUsers().call()
    assert len(all_activated) >= len(activated_users), \
        "Количество активированных пользователей не соответствует ожидаемому"
    
    # Проверяем что все наши пользователи есть в списке
    for user_address in activated_users:
        assert user_address in all_activated, \
            f"Пользователь {user_address} отсутствует в списке активированных"

def test_user_invite_count(web3, invite_nft_contract, seller_account, user_account):
    """
    Проверка подсчета инвайтов пользователя:
    - Счетчик увеличивается при получении инвайтов
    - Счетчик корректно отражает количество инвайтов пользователя
    """
    # Проверяем начальное значение
    initial_count = invite_nft_contract.functions.userInviteCount(user_account.address).call()
    assert initial_count == 0, "Начальное количество инвайтов должно быть 0"
    
    # Минтим инвайт для активации
    code = generate_invite_code(prefix="count_test")
    tx_hash = invite_nft_contract.functions.mintInvites([code], 0).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Активируем инвайт для пользователя (получает 12 новых)
    new_codes = [generate_invite_code(prefix="count_new") for _ in range(12)]
    tx_hash = invite_nft_contract.functions.activateAndMintInvites(
        code, user_account.address, new_codes, 0
    ).transact({'from': seller_account.address})
    web3.eth.wait_for_transaction_receipt(tx_hash)
    
    # Проверяем количество инвайтов пользователя через getUserInvites
    user_invites = invite_nft_contract.functions.getUserInvites(user_account.address).call()
    assert len(user_invites) == 12, "Пользователь должен иметь 12 инвайтов"
    
    # Проверяем счетчик
    final_count = invite_nft_contract.functions.userInviteCount(user_account.address).call()
    assert final_count == 12, "userInviteCount должен показывать 12 инвайтов"
    
    # Проверяем что все инвайты принадлежат пользователю
    for token_id in user_invites:
        owner = invite_nft_contract.functions.ownerOf(token_id).call()
        assert owner == user_account.address, f"Инвайт {token_id} не принадлежит пользователю"
        
        # Проверяем что инвайт есть в истории пользователя
        history = invite_nft_contract.functions.getInviteTransferHistory(token_id).call()
        assert user_account.address in history, f"Инвайт {token_id} отсутствует в истории пользователя"
 