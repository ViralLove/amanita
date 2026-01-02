"""
Integration tests for bridge mechanism (creating capacity nodes for next generation).

Tests:
1. find_bridge_gaps() - поиск резервных щелей
2. create_bridge_to_next_generation() - создание моста к следующему поколению
3. Валидация что мост создает новых активаторов с capacity = 12/12
"""

import pytest
from web3 import Web3


@pytest.mark.integration
def test_find_bridge_gaps(network_state_tracker, spiral_engine_contract):
    """
    Тест поиска резервных щелей через find_bridge_gaps().
    
    Проверяет:
    - Метод находит активаторов с capacity >= min_gap_size
    - Результат отсортирован по generation (lowest first) и capacity (highest first)
    - Ограничение max_gaps работает корректно
    """
    tracker = network_state_tracker
    
    # 1. Найти щели с минимальным размером = 1
    gaps = tracker.find_bridge_gaps(min_gap_size=1, max_gaps=10)
    
    # 2. Проверяем что результат - список
    assert isinstance(gaps, list), "find_bridge_gaps должен возвращать список"
    
    # 3. Если есть щели, проверяем их структуру и валидность
    if gaps:
        for gap in gaps:
            # Проверяем структуру dict
            assert isinstance(gap, dict), f"Каждый gap должен быть dict, got {type(gap)}"
            assert 'address' in gap, "gap должен содержать 'address'"
            assert 'capacity' in gap, "gap должен содержать 'capacity'"
            assert 'generation' in gap, "gap должен содержать 'generation'"
            
            # Проверяем что capacity >= min_gap_size
            assert gap['capacity'] >= 1, f"Capacity должен быть >= 1, got {gap['capacity']}"
            
            # Проверяем что generation не None
            assert gap['generation'] is not None, "Generation не должен быть None"
            
            # Проверяем валидность capacity через прямой запрос к контракту
            circle = spiral_engine_contract.functions.getCircleMembers(gap['address']).call()
            actual_capacity = 12 - len(circle)
            assert actual_capacity == gap['capacity'], (
                f"Capacity mismatch: reported={gap['capacity']}, actual={actual_capacity}"
            )
        
        # 4. Проверяем сортировку: по generation (lowest first), затем capacity (highest first)
        if len(gaps) > 1:
            for i in range(len(gaps) - 1):
                current = gaps[i]
                next_gap = gaps[i + 1]
                
                # Generation должна быть отсортирована по возрастанию
                assert current['generation'] <= next_gap['generation'], (
                    f"Gaps не отсортированы по generation: {current['generation']} > {next_gap['generation']}"
                )
                
                # Если generation одинаковые, capacity должна быть отсортирована по убыванию
                if current['generation'] == next_gap['generation']:
                    assert current['capacity'] >= next_gap['capacity'], (
                        f"Gaps с одинаковым generation не отсортированы по capacity: "
                        f"{current['capacity']} < {next_gap['capacity']}"
                    )
        
        print(f"✅ Found {len(gaps)} bridge gaps (min_gap_size=1)")
        for i, gap in enumerate(gaps[:5]):  # Показываем первые 5
            print(f"   Gap {i+1}: Gen {gap['generation']}, {gap['address'][:10]}..., capacity={gap['capacity']}/12")
    else:
        print("⚠️  No bridge gaps found (network may be fully saturated)")
    
    # 5. Проверяем ограничение max_gaps
    gaps_limited = tracker.find_bridge_gaps(min_gap_size=1, max_gaps=3)
    assert len(gaps_limited) <= 3, f"Ограничение max_gaps не работает: got {len(gaps_limited)} > 3"
    
    # 6. Проверяем фильтрацию по min_gap_size
    gaps_large = tracker.find_bridge_gaps(min_gap_size=5, max_gaps=10)
    if gaps_large:
        for gap in gaps_large:
            assert gap['capacity'] >= 5, f"min_gap_size фильтрация не работает: capacity={gap['capacity']} < 5"


@pytest.mark.integration
def test_create_bridge_to_next_generation(exponential_activator_pool, spiral_engine_contract, web3):
    """
    Тест создания моста к следующему поколению через create_bridge_to_next_generation().
    
    Проверяет:
    - Мост создается через резервные щели
    - Новые пользователи активированы
    - Новые активаторы имеют необходимые роли
    - Возвращается правильное количество новых активаторов
    """
    pool = exponential_activator_pool
    
    # 1. Получить текущее состояние сети
    state_before = pool.tracker.refresh_state(force=True)
    users_before = state_before['total_users']
    
    print(f"📊 Network state before bridge: {users_before} users")
    
    # 2. Проверить наличие щелей для создания моста
    gaps = pool.tracker.find_bridge_gaps(min_gap_size=1, max_gaps=2)
    
    if len(gaps) < 2:
        pytest.skip(f"Insufficient bridge gaps for test: found {len(gaps)}, need 2. "
                   f"Network may be fully saturated.")
    
    # 3. Создать мост (2 новых активатора для быстроты теста)
    bridge_activators = pool.create_bridge_to_next_generation(bridge_size=2, min_gap_size=1)
    
    # 4. Проверяем результат
    assert isinstance(bridge_activators, list), "create_bridge_to_next_generation должен возвращать список"
    assert len(bridge_activators) == 2, f"Ожидали 2 новых активатора, получили {len(bridge_activators)}"
    
    # 5. Проверяем структуру каждого элемента
    for i, (new_activator_account, invite_code) in enumerate(bridge_activators):
        # Проверяем "контракт" account (duck-typing), а не конкретный класс.
        # Причина: web3.eth.account.create() возвращает LocalAccount, и строгий isinstance(Account)
        # здесь даёт ложное падение при корректной функциональности.
        assert hasattr(new_activator_account, "address"), (
            f"Элемент {i} должен иметь address, got {type(new_activator_account)}"
        )
        assert Web3.is_address(new_activator_account.address), (
            f"Элемент {i} должен иметь валидный address, got {new_activator_account.address!r}"
        )
        assert hasattr(new_activator_account, "sign_transaction"), (
            f"Элемент {i} должен уметь подписывать транзакции (sign_transaction), got {type(new_activator_account)}"
        )
        
        # Проверяем тип invite_code
        assert isinstance(invite_code, str), (
            f"Invite code должен быть str, got {type(invite_code)}"
        )
        assert len(invite_code) > 0, "Invite code не должен быть пустым"
        
        # 6. Проверяем что новый пользователь активирован
        # Проверяем через контракт что пользователь в списке активированных
        try:
            # Проверяем что пользователь активирован (есть в activatedUsers)
            all_users = []
            j = 0
            while True:
                try:
                    user = spiral_engine_contract.functions.activatedUsers(j).call()
                    all_users.append(user.lower())
                    j += 1
                except:
                    break
            
            assert new_activator_account.address.lower() in all_users, (
                f"Новый активатор {new_activator_account.address[:10]}... не найден в activatedUsers"
            )
        except Exception as e:
            pytest.fail(f"Failed to verify activation for {new_activator_account.address[:10]}...: {e}")
        
        # 7. Проверяем что новый активатор имеет роли
        ACTIVATOR_ROLE = web3.keccak(text="ACTIVATOR_ROLE")
        SELLER_ROLE = web3.keccak(text="SELLER_ROLE")
        
        has_activator = spiral_engine_contract.functions.hasRole(
            ACTIVATOR_ROLE, new_activator_account.address
        ).call()
        has_seller = spiral_engine_contract.functions.hasRole(
            SELLER_ROLE, new_activator_account.address
        ).call()
        
        assert has_activator, (
            f"Новый активатор {new_activator_account.address[:10]}... не имеет ACTIVATOR_ROLE"
        )
        assert has_seller, (
            f"Новый активатор {new_activator_account.address[:10]}... не имеет SELLER_ROLE"
        )
        
        # 8. Проверяем что инвайт существует и принадлежит новому активатору
        token_id = spiral_engine_contract.functions.inviteCodeToTokenId(invite_code).call()
        assert token_id > 0, f"Invite code {invite_code} не найден в контракте"
        
        invite_owner = spiral_engine_contract.functions.ownerOf(token_id).call()
        assert invite_owner.lower() == new_activator_account.address.lower(), (
            f"Invite {invite_code} не принадлежит новому активатору. "
            f"Owner: {invite_owner[:10]}..., Expected: {new_activator_account.address[:10]}..."
        )
        
        print(f"✅ Bridge activator {i+1}/2 validated: {new_activator_account.address[:10]}... "
              f"(has roles, activated, has invite)")
    
    # 9. Проверяем что сеть выросла
    state_after = pool.tracker.refresh_state(force=True)
    users_after = state_after['total_users']
    
    assert users_after == users_before + 2, (
        f"Network should grow by 2 users: before={users_before}, after={users_after}"
    )
    
    print(f"✅ Bridge created successfully: network grew from {users_before} to {users_after} users")


@pytest.mark.integration
def test_bridge_creates_new_activators(exponential_activator_pool, spiral_engine_contract, web3):
    """
    Тест что мост создает новых активаторов с capacity = 12/12.
    
    Проверяет:
    - Каждый новый активатор имеет пустой круг (capacity = 12/12)
    - Новые активаторы могут быть использованы для дальнейших активаций
    - Состояние сети обновлено корректно
    """
    pool = exponential_activator_pool
    
    # 1. Получить текущее состояние
    state_before = pool.tracker.refresh_state(force=True)
    users_before = state_before['total_users']
    
    # 2. Проверить наличие щелей
    gaps = pool.tracker.find_bridge_gaps(min_gap_size=1, max_gaps=2)
    
    if len(gaps) < 2:
        pytest.skip(f"Insufficient bridge gaps for test: found {len(gaps)}, need 2. "
                   f"Network may be fully saturated.")
    
    # 3. Создать мост
    bridge_activators = pool.create_bridge_to_next_generation(bridge_size=2, min_gap_size=1)
    
    assert len(bridge_activators) == 2, f"Ожидали 2 новых активатора, получили {len(bridge_activators)}"
    
    # 4. Проверяем что каждый новый активатор имеет capacity = 12/12
    for i, (new_activator_account, invite_code) in enumerate(bridge_activators):
        # Получаем круг нового активатора
        circle = spiral_engine_contract.functions.getCircleMembers(new_activator_account.address).call()
        circle_size = len(circle)
        capacity = 12 - circle_size
        
        # Новый активатор должен иметь capacity = 12/12 (круг пуст)
        assert capacity == 12, (
            f"Новый активатор {new_activator_account.address[:10]}... должен иметь capacity=12/12, "
            f"got capacity={capacity}/12 (circle_size={circle_size})"
        )
        assert circle_size == 0, (
            f"Новый активатор должен иметь пустой круг, got circle_size={circle_size}"
        )
        
        print(f"✅ Bridge activator {i+1}/2 has capacity={capacity}/12 (circle_size={circle_size})")
        
        # 5. Проверяем что новый активатор может быть найден через find_activators_with_capacity
        available = pool.tracker.find_activators_with_capacity()
        
        # Ищем нового активатора в списке доступных
        found = False
        for act in available:
            if act['address'].lower() == new_activator_account.address.lower():
                assert act['capacity'] == 12, (
                    f"Новый активатор найден с capacity={act['capacity']}, ожидали 12"
                )
                found = True
                break
        
        assert found, (
            f"Новый активатор {new_activator_account.address[:10]}... не найден в "
            f"find_activators_with_capacity() (должен иметь capacity=12)"
        )
        
        print(f"✅ Bridge activator {i+1}/2 found in available activators list")
    
    # 6. Проверяем что состояние сети обновлено
    state_after = pool.tracker.refresh_state(force=True)
    users_after = state_after['total_users']
    
    assert users_after == users_before + 2, (
        f"Network state updated: before={users_before}, after={users_after}"
    )
    
    # 7. Проверяем что новые активаторы можно использовать для дальнейших активаций
    # (опционально: можем попробовать получить их через get_next, но это может быть сложно
    # из-за round-robin логики, поэтому просто проверяем что они доступны)
    
    print(f"✅ Bridge creates new activators with capacity 12/12 successfully")


@pytest.mark.integration
def test_bridge_insufficient_gaps_error(exponential_activator_pool):
    """
    Тест обработки ошибки при недостаточном количестве щелей.
    
    Проверяет:
    - RuntimeError поднимается когда недостаточно щелей для создания моста
    - Сообщение об ошибке информативно
    """
    pool = exponential_activator_pool
    
    # Пытаемся создать мост с очень большим bridge_size
    # (больше чем доступно щелей в сети)
    with pytest.raises(RuntimeError) as exc_info:
        pool.create_bridge_to_next_generation(bridge_size=100, min_gap_size=1)
    
    # Проверяем что ошибка содержит информативное сообщение
    error_msg = str(exc_info.value)
    assert "Insufficient bridge gaps" in error_msg, (
        f"Ошибка должна содержать 'Insufficient bridge gaps', got: {error_msg}"
    )
    assert "100" in error_msg or "needed" in error_msg, (
        f"Ошибка должна содержать информацию о требуемом количестве, got: {error_msg}"
    )
    
    print(f"✅ Insufficient gaps error handled correctly: {error_msg[:100]}...")

