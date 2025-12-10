import pytest
import os
import sys
import json
import time
import string
import random
from pathlib import Path
from dotenv import load_dotenv
from eth_account import Account

# Add bot/ to Python path for imports (fixes import issues)
bot_dir = Path(__file__).parent.parent
if str(bot_dir) not in sys.path:
    sys.path.insert(0, str(bot_dir))

# Absolute imports for services (work with bot_dir in sys.path)
from services.common.translation_cache_service import TranslationCacheService
from services.common.multilingual_ipfs_service import MultilingualIPFSService
from services.common.localization_service import LocalizationService

# Stub imports are lazy-loaded in fixtures to avoid import errors (see fixtures below)

# Загружаем .env (паттерн из test_product_registry_integration.py:49)
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

# Устанавливаем профиль localhost (паттерн из test_blockchain.py:8)
os.environ["BLOCKCHAIN_PROFILE"] = "localhost"


# ═══════════════════════════════════════════════════════════════
# NETWORK GROWTH INFRASTRUCTURE (Exponential Growth Strategy)
# ═══════════════════════════════════════════════════════════════

class NetworkStateTracker:
    """
    Отслеживает состояние сети активаций в SpiralEngine.
    Queries on-chain state и кэширует для performance.
    Works на ЛЮБОМ network state (0 users → 1000+ users).
    """
    
    def __init__(self, contract, web3):
        self.contract = contract
        self.web3 = web3
        self._cache = None
        self._cache_timestamp = None
    
    def refresh_state(self, force=False):
        """
        Загружает текущее состояние сети из контракта.
        Uses cache если не force и cache < 60 seconds old.
        
        Builds ALL generations using BFS traversal (Gen 0, 1, 2, 3, 4+...).
        Supports deep networks with unlimited generation depth.
        """
        # Check cache validity
        if not force and self._cache and self._cache_timestamp:
            age = time.time() - self._cache_timestamp
            if age < 60:  # Cache valid для 60 seconds
                return self._cache
        
        # Query on-chain state
        print("🔍 Querying network state from local network...")
        
        # Get all activated users
        all_users = []
        try:
            # Iterate through public array (activatedUsers is public address[])
            i = 0
            while True:
                user = self.contract.functions.activatedUsers(i).call()
                all_users.append(user)
                i += 1
        except:
            pass  # Reached end of array
        
        # Build state object
        state = {
            'total_users': len(all_users),
            'users': all_users,
            'generations': {},
            'circles': {},
            'capacities': {}
        }
        
        # Deployer is always generation 0
        deployer = os.getenv('DEPLOYER_ADDRESS')
        if not deployer:
            raise RuntimeError("DEPLOYER_ADDRESS not found in environment")
        
        # Build ALL generations using BFS traversal
        self._build_all_generations_bfs(state, deployer, all_users)
        
        # Cache result
        self._cache = state
        self._cache_timestamp = time.time()
        
        # Log summary
        max_gen = max(state['generations'].keys()) if state['generations'] else 0
        print(f"✅ Network state: {state['total_users']} users, generations 0-{max_gen}")
        for gen in sorted(state['generations'].keys()):
            gen_users = state['generations'][gen]
            print(f"   Gen {gen}: {len(gen_users)} users")
        
        return state
    
    def _build_all_generations_bfs(self, state, deployer, all_users):
        """
        Builds ALL generations using BFS traversal.
        
        Algorithm:
        1. Start with deployer (Gen 0)
        2. For each user in current generation, get their circle members
        3. Circle members become next generation
        4. Continue until no new users found
        5. Store capacities for all users during traversal
        """
        # Initialize generations
        state['generations'][0] = [deployer]
        
        # Get deployer's circle and capacity
        deployer_circle = self.contract.functions.getCircleMembers(deployer).call()
        state['circles'][deployer] = deployer_circle
        state['capacities'][deployer] = 12 - len(deployer_circle)
        
        # BFS queue: (generation, user_address)
        # Start with Gen 0 (deployer)
        queue = [(0, deployer)]
        visited = {deployer.lower()}
        
        # Map user → generation for lookup
        user_to_generation = {deployer.lower(): 0}
        
        while queue:
            gen, user = queue.pop(0)
            
            # Get circle members for this user
            try:
                circle = self.contract.functions.getCircleMembers(user).call()
            except Exception:
                circle = []
            
            # Store circle and capacity
            state['circles'][user] = circle
            state['capacities'][user] = 12 - len(circle)
            
            # Process circle members (next generation)
            next_gen = gen + 1
            
            for member in circle:
                member_lower = member.lower()
                
                # Skip if already visited (handles cycles/duplicates)
                if member_lower in visited:
                    continue
                
                visited.add(member_lower)
                user_to_generation[member_lower] = next_gen
                
                # Add to next generation
                if next_gen not in state['generations']:
                    state['generations'][next_gen] = []
                state['generations'][next_gen].append(member)
                
                # Add to queue for further traversal
                queue.append((next_gen, member))
        
        # Handle any activated users that weren't reached via BFS
        # (shouldn't happen in correct network, but handle edge cases)
        for user in all_users:
            user_lower = user.lower()
            if user_lower not in visited:
                # Try to determine generation from userActivator
                try:
                    activator = self.contract.functions.userActivator(user).call()
                    if activator and activator.lower() != '0x0000000000000000000000000000000000000000':
                        activator_gen = user_to_generation.get(activator.lower())
                        if activator_gen is not None:
                            user_gen = activator_gen + 1
                            user_to_generation[user_lower] = user_gen
                            
                            if user_gen not in state['generations']:
                                state['generations'][user_gen] = []
                            state['generations'][user_gen].append(user)
                            visited.add(user_lower)
                            
                            # Get circle and capacity
                            try:
                                circle = self.contract.functions.getCircleMembers(user).call()
                            except Exception:
                                circle = []
                            state['circles'][user] = circle
                            state['capacities'][user] = 12 - len(circle)
                except Exception:
                    # User without activator or query failed - skip
                    pass
        
        # Ensure all users have capacities (for users not in circles)
        for user in all_users:
            user_lower = user.lower()
            if user_lower not in state['capacities']:
                # Query capacity
                try:
                    circle = self.contract.functions.getCircleMembers(user).call()
                    state['circles'][user] = circle
                    state['capacities'][user] = 12 - len(circle)
                except Exception:
                    state['circles'][user] = []
                    state['capacities'][user] = 12
    
    def get_generation_level(self, user_address):
        """
        Определяет generation level пользователя.
        Returns None if user not found in any generation.
        """
        state = self.refresh_state()
        
        user_lower = user_address.lower()
        
        for gen, users in state['generations'].items():
            # Case-insensitive comparison
            for user in users:
                if user.lower() == user_lower:
                    return gen
        
        return None  # User not found
    
    def log_network_diagnostics(self):
        """
        Выводит подробную диагностическую информацию о состоянии сети.
        
        Логирует:
        - Общее количество активированных пользователей
        - Распределение по поколениям (generations)
        - Количество активаторов с capacity > 0
        - Детальную информацию о capacity по каждому активатору
        - Топ активаторов с наибольшим capacity
        """
        state = self.refresh_state(force=True)
        
        print("\n" + "="*80)
        print("🔍 NETWORK DIAGNOSTICS - Состояние сети")
        print("="*80)
        
        # 1. Общая статистика
        print(f"\n📊 Общая статистика:")
        print(f"   • Всего активированных пользователей: {state['total_users']}")
        
        # 2. Распределение по поколениям
        if state['generations']:
            max_gen = max(state['generations'].keys())
            print(f"\n🌳 Распределение по поколениям (0-{max_gen}):")
            for gen in sorted(state['generations'].keys()):
                gen_users = state['generations'][gen]
                print(f"   • Gen {gen}: {len(gen_users)} пользователей")
        
        # 3. Capacity анализ
        print(f"\n💎 Capacity анализ:")
        
        # Собираем всех активаторов с их capacity
        activators_with_capacity = []
        activators_full = []
        
        for user_addr in state['users']:
            try:
                circle = self.contract.functions.getCircleMembers(user_addr).call()
                capacity = 12 - len(circle)
                generation = self.get_generation_level(user_addr)
                
                if capacity > 0:
                    activators_with_capacity.append({
                        'address': user_addr,
                        'capacity': capacity,
                        'generation': generation if generation is not None else -1,
                        'circle_size': len(circle)
                    })
                elif len(circle) >= 12:
                    activators_full.append({
                        'address': user_addr,
                        'generation': generation if generation is not None else -1
                    })
            except Exception as e:
                # Skip errors
                continue
        
        # Проверяем deployer отдельно
        deployer = os.getenv('DEPLOYER_ADDRESS')
        if deployer:
            try:
                circle = self.contract.functions.getCircleMembers(deployer).call()
                capacity = 12 - len(circle)
                if capacity > 0:
                    # Добавляем только если его еще нет в списке
                    if not any(a['address'].lower() == deployer.lower() for a in activators_with_capacity):
                        activators_with_capacity.append({
                            'address': deployer,
                            'capacity': capacity,
                            'generation': 0,
                            'circle_size': len(circle)
                        })
                elif len(circle) >= 12:
                    if not any(a['address'].lower() == deployer.lower() for a in activators_full):
                        activators_full.append({
                            'address': deployer,
                            'generation': 0
                        })
            except Exception as e:
                pass
        
        print(f"   • Активаторов с capacity > 0: {len(activators_with_capacity)}")
        print(f"   • Активаторов с полным кругом (12/12): {len(activators_full)}")
        
        # 4. Детальная информация о активаторах с capacity
        if activators_with_capacity:
            print(f"\n✅ Активаторы с доступным capacity ({len(activators_with_capacity)}):")
            
            # Сортируем по generation, затем по capacity (desc)
            activators_with_capacity.sort(key=lambda x: (x['generation'], -x['capacity']))
            
            # Группируем по generation
            by_generation = {}
            for act in activators_with_capacity:
                gen = act['generation']
                if gen not in by_generation:
                    by_generation[gen] = []
                by_generation[gen].append(act)
            
            # Выводим по поколениям
            for gen in sorted(by_generation.keys()):
                gen_activators = by_generation[gen]
                print(f"   Gen {gen}: {len(gen_activators)} активаторов")
                for act in gen_activators[:10]:  # Показываем первые 10
                    print(f"      • {act['address'][:10]}...: capacity={act['capacity']}/12, circle={act['circle_size']}/12")
                if len(gen_activators) > 10:
                    print(f"      ... и еще {len(gen_activators) - 10} активаторов")
        else:
            print(f"\n⚠️  ВНИМАНИЕ: Нет активаторов с доступным capacity!")
            print(f"   Сеть может быть полностью заполнена или требуется деплой новых активаторов.")
        
        # 5. Статистика по полным активаторам (первые 5)
        if activators_full and len(activators_full) <= 5:
            print(f"\n📦 Полные активаторы (12/12) - первые 5:")
            for act in activators_full[:5]:
                print(f"   • Gen {act['generation']}: {act['address'][:10]}...")
        
        print("="*80 + "\n")
    
    def find_activators_with_capacity(self):
        """
        Находит всех activators с доступным capacity в круге.
        ВСЕГДА делает прямой запрос к контракту (без кэша для capacity).
        Возвращает отсортированных по generation (lowest first).
        """
        state = self.refresh_state()
        
        activators = []
        processed_addresses = set()
        
        # Strategy: Check ALL activated users from contract with DIRECT query (no cache for capacity)
        for user_addr in state['users']:
            user_lower = user_addr.lower()
            if user_lower in processed_addresses:
                continue
            processed_addresses.add(user_lower)
            
            # ALWAYS query capacity directly from contract (never use cache)
            try:
                circle = self.contract.functions.getCircleMembers(user_addr).call()
                capacity = 12 - len(circle)
                
                # Only add if capacity > 0
                if capacity > 0:
                    generation = self.get_generation_level(user_addr)
                    if generation is not None:
                        activators.append({
                            'address': user_addr,
                            'capacity': capacity,
                            'generation': generation
                        })
            except Exception as e:
                # Skip this user if query fails (may not be activated or contract error)
                # Log for debugging but don't fail
                print(f"⚠️ Failed to query capacity for {user_addr[:10]}...: {e}")
                continue
        
        # Also check deployer directly (always)
        deployer = os.getenv('DEPLOYER_ADDRESS')
        if deployer:
            deployer_lower = deployer.lower()
            if deployer_lower not in processed_addresses:
                try:
                    circle = self.contract.functions.getCircleMembers(deployer).call()
                    capacity = 12 - len(circle)
                    if capacity > 0:
                        generation = self.get_generation_level(deployer)
                        if generation is None:
                            generation = 0  # Deployer is always Gen 0
                        activators.append({
                            'address': deployer,
                            'capacity': capacity,
                            'generation': generation
                        })
                except Exception as e:
                    print(f"⚠️ Failed to query capacity for deployer: {e}")
        
        # Sort by generation (lowest first for breadth-first)
        activators.sort(key=lambda x: (x['generation'], -x['capacity']))
        
        return activators
    
    def find_bridge_gaps(
        self,
        min_gap_size: int = 1,
        max_gaps: int = 10
    ):
        """
        Находит резервные щели (активаторы с capacity >= min_gap_size),
        которые можно использовать для создания моста.
        
        ВСЕГДА делает прямой запрос к контракту (без кэша для capacity).
        
        Args:
            min_gap_size: Минимальная capacity для использования как щели (default: 1)
            max_gaps: Максимальное количество щелей для возврата (default: 10)
        
        Returns:
            List[Dict]: List of activator dicts с capacity >= min_gap_size,
            отсортированных по generation (lowest first) и capacity (highest first).
            Каждый dict содержит: {'address': str, 'capacity': int, 'generation': int}
            Ограничено max_gaps элементами.
        """
        state = self.refresh_state()
        
        gaps = []
        processed_addresses = set()
        
        # Strategy: Check ALL activated users from contract with DIRECT query (no cache for capacity)
        for user_addr in state['users']:
            user_lower = user_addr.lower()
            if user_lower in processed_addresses:
                continue
            processed_addresses.add(user_lower)
            
            # ALWAYS query capacity directly from contract (never use cache)
            try:
                circle = self.contract.functions.getCircleMembers(user_addr).call()
                capacity = 12 - len(circle)
                
                # Only add if capacity >= min_gap_size (allows filtering by gap size)
                if capacity >= min_gap_size:
                    generation = self.get_generation_level(user_addr)
                    if generation is not None:
                        gaps.append({
                            'address': user_addr,
                            'capacity': capacity,
                            'generation': generation
                        })
            except Exception as e:
                # Skip this user if query fails (may not be activated or contract error)
                # Log for debugging but don't fail
                print(f"⚠️ Failed to query capacity for {user_addr[:10]}...: {e}")
                continue
        
        # Also check deployer directly (always)
        deployer = os.getenv('DEPLOYER_ADDRESS')
        if deployer:
            deployer_lower = deployer.lower()
            if deployer_lower not in processed_addresses:
                try:
                    circle = self.contract.functions.getCircleMembers(deployer).call()
                    capacity = 12 - len(circle)
                    if capacity >= min_gap_size:
                        generation = self.get_generation_level(deployer)
                        if generation is None:
                            generation = 0  # Deployer is always Gen 0
                        gaps.append({
                            'address': deployer,
                            'capacity': capacity,
                            'generation': generation
                        })
                except Exception as e:
                    print(f"⚠️ Failed to query capacity for deployer: {e}")
        
        # Sort by generation (lowest first), then by capacity (highest first)
        gaps.sort(key=lambda x: (x['generation'], -x['capacity']))
        
        # Limit to max_gaps
        return gaps[:max_gaps]


class DeterministicAccountManager:
    """
    Управляет test accounts с детерминированными ключами.
    Позволяет recreate accounts для reuse как activators.
    """
    
    def __init__(self, web3, deployer_account):
        self.web3 = web3
        self.deployer = deployer_account
        self._accounts_cache = {}  # index → Account
        self._address_to_index = {}  # address → index
        self._anvil_accounts = {}  # address → Account (Anvil pre-funded)
        
        # Load Anvil pre-funded accounts for Gen1+ users
        self._load_anvil_accounts()
    
    def _load_anvil_accounts(self):
        """
        Load Anvil pre-funded accounts from default mnemonic.
        
        Anvil (Foundry) provides 1000 pre-funded accounts:
        - Mnemonic: "test test test test test test test test test test test junk"
        - HD path: m/44'/60'/0'/0/{index}
        - All accounts pre-funded with 10000 ETH
        - All unlocked (can use .transact() без explicit signing)
        
        Loading 1000 accounts (full range) for comprehensive network growth testing.
        """
        from eth_account import Account
        
        # Enable mnemonic features
        Account.enable_unaudited_hdwallet_features()
        
        # Anvil/Hardhat default mnemonic
        mnemonic = "test test test test test test test test test test test junk"
        
        loaded_count = 0
        for i in range(1000):  # Load full range (1000 accounts as per Anvil docs)
            try:
                account = Account.from_mnemonic(
                    mnemonic,
                    account_path=f"m/44'/60'/0'/0/{i}"
                )
                self._anvil_accounts[account.address.lower()] = account
                loaded_count += 1
            except Exception as e:
                if i < 3:  # Log only first 3 errors
                    print(f"⚠️  Failed to load Anvil account #{i}: {e}")
                continue
        
        print(f"✅ Loaded {loaded_count} Anvil accounts for Gen1+ users (exponential network growth ready)")
    
    def _lazy_load_anvil_account(self, address):
        """
        Lazy load Anvil account if not already loaded.
        Searches through extended range if needed.
        
        Returns Account if found, None otherwise.
        """
        addr_lower = address.lower()
        
        # Already loaded?
        if addr_lower in self._anvil_accounts:
            return self._anvil_accounts[addr_lower]
        
        # Try to load from extended range (1000-2000)
        from eth_account import Account
        mnemonic = "test test test test test test test test test test test junk"
        
        for i in range(1000, 2000):  # Extended range
            try:
                account = Account.from_mnemonic(
                    mnemonic,
                    account_path=f"m/44'/60'/0'/0/{i}"
                )
                # Cache it
                self._anvil_accounts[account.address.lower()] = account
                
                if account.address.lower() == addr_lower:
                    return account
            except Exception:
                continue
        
        return None
    
    def get_or_create_account(self, index):
        """
        Создает или возвращает account с детерминированным ключом.
        Для одного index всегда один и тот же ключ.
        """
        if index in self._accounts_cache:
            return self._accounts_cache[index]
        
        # Generate deterministic key
        seed = f"amanita_test_user_{index:06d}"
        private_key = self.web3.keccak(text=seed)
        account = Account.from_key(private_key)
        
        # Cache
        self._accounts_cache[index] = account
        self._address_to_index[account.address.lower()] = index
        
        return account
    
    def get_account_by_address(self, address):
        """
        Maps on-chain address to known account with private key.
        
        Priority:
        1. Deployer (fixed from .env)
        2. Anvil pre-funded accounts (0-1000 loaded, extended range 1000-2000 lazy-loaded)
        3. Deterministic created accounts
        4. Create new deterministic account based on address hash (for unknown addresses from saved network state)
        """
        addr_lower = address.lower()
        
        # Priority 1: Deployer (always return deployer for deployer address)
        if addr_lower == self.deployer.address.lower():
            return self.deployer
        
        # Priority 2: Anvil pre-funded accounts (PRIMARY PATH for Gen1+ users)
        if addr_lower in self._anvil_accounts:
            # Found matching Anvil account - has known private key!
            return self._anvil_accounts[addr_lower]
        
        # Priority 2b: Lazy load from extended range
        lazy_account = self._lazy_load_anvil_account(address)
        if lazy_account:
            return lazy_account
        
        # Priority 3: Previously created deterministic accounts (legacy)
        if addr_lower in self._address_to_index:
            index = self._address_to_index[addr_lower]
            return self._accounts_cache[index]
        
        # Priority 4: Create deterministic account from address hash
        # This handles cases where address exists in network but key is unknown
        # (e.g., from saved Anvil state where activation was done manually)
        print(f"⚠️  Address {address[:10]}... not in Anvil accounts, creating deterministic account from hash")
        
        # Create deterministic private key from address
        # Use keccak hash of address as seed
        seed = f"amanita_network_user_{address}"
        private_key = self.web3.keccak(text=seed)
        
        try:
            from eth_account import Account
            account = Account.from_key(private_key)
            
            # Cache it for future use
            self._address_to_index[addr_lower] = len(self._accounts_cache)
            self._accounts_cache[len(self._accounts_cache)] = account
            
            print(f"✅ Created deterministic account for {address[:10]}... (needs funding and roles)")
            return account
        except Exception as e:
            raise RuntimeError(
                f"Cannot create account for address {address}. "
                f"Address is not in Anvil pre-funded accounts (0-2000 range) "
                f"and failed to create deterministic account: {e}"
            )
    
    def ensure_funded(self, account, min_balance_eth=0.5):
        """Ensure account has sufficient ETH balance"""
        balance = self.web3.eth.get_balance(account.address)
        balance_eth = self.web3.from_wei(balance, 'ether')
        
        if balance_eth < min_balance_eth:
            # Transfer from deployer
            tx_hash = self.web3.eth.send_transaction({
                'from': self.deployer.address,
                'to': account.address,
                'value': self.web3.to_wei(min_balance_eth, 'ether')
            })
            self.web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"💰 Funded {account.address[:10]}... with {min_balance_eth} ETH")
    
    def ensure_roles(self, account, contract, roles=['ACTIVATOR_ROLE', 'SELLER_ROLE']):
        """Ensure account has required roles"""
        for role_name in roles:
            role_hash = self.web3.keccak(text=role_name)
            has_role = contract.functions.hasRole(role_hash, account.address).call()
            
            if not has_role:
                # Grant from deployer
                tx_hash = contract.functions.grantRole(role_hash, account.address).transact({
                    'from': self.deployer.address
                })
                self.web3.eth.wait_for_transaction_receipt(tx_hash)
                print(f"🔑 Granted {role_name} to {account.address[:10]}...")


class ExponentialActivatorPool:
    """
    Интеллектуальный пул activators для exponential network growth.
    
    Features:
    - Breadth-first strategy (заполняет generation целиком перед переходом к следующей)
    - Round-robin selection within generation (balanced fill)
    - Works на любом network state (0 users → 1000+ users)
    - Auto-mints invites для selected activator
    - Auto-grants roles если нужно
    """
    
    def __init__(self, network_tracker, account_manager, contract, web3):
        self.tracker = network_tracker
        self.accounts = account_manager
        self.contract = contract
        self.web3 = web3
        self.round_robin = {}  # generation → index
        self._minted_count = 0
    
    def get_next(self, max_retries=3):
        """
        Возвращает (activator_account, invite_code) для следующей активации.
        Автоматически retry при обнаружении capacity=0 (race condition protection).
        
        Args:
            max_retries: Максимальное количество попыток (default: 3)
        
        Returns:
            tuple: (activator_account, invite_code)
        
        Raises:
            RuntimeError: Если не удалось найти активатора с capacity после всех попыток
        """
        for attempt in range(max_retries):
            # 1. Refresh network state (force refresh on retry)
            if attempt > 0:
                self.tracker.refresh_state(force=True)
            state = self.tracker.refresh_state()
            
            # 2. Find activators with capacity
            available = self.tracker.find_activators_with_capacity()
            
            if not available:
                if attempt < max_retries - 1:
                    print(f"⚠️ Attempt {attempt+1}/{max_retries}: No activators with capacity found, retrying...")
                    continue
                else:
                    raise RuntimeError(
                        f"No activators with capacity found after {max_retries} attempts. "
                        f"Network may be fully saturated."
                    )
            
            # 3. Exponential strategy: select from lowest generation
            # Group by generation
            by_generation = {}
            for act in available:
                gen = act['generation']
                if gen not in by_generation:
                    by_generation[gen] = []
                by_generation[gen].append(act)
            
            # Select lowest generation
            lowest_gen = min(by_generation.keys())
            gen_activators = by_generation[lowest_gen]
            
            # 4. Round-robin within generation
            rr_index = self.round_robin.get(lowest_gen, 0)
            selected = gen_activators[rr_index % len(gen_activators)]
            self.round_robin[lowest_gen] = rr_index + 1
            
            print(f"🎯 Selected: Gen {lowest_gen}, {selected['address'][:10]}..., capacity: {selected['capacity']}/12")
            
            # 5. Get account with private key
            activator_account = self.accounts.get_account_by_address(selected['address'])
            
            # 6. CRITICAL: Validate capacity directly from contract before returning
            # This prevents race conditions where capacity changed between selection and return
            try:
                circle = self.contract.functions.getCircleMembers(selected['address']).call()
                actual_capacity = 12 - len(circle)
                
                if actual_capacity <= 0:
                    print(f"⚠️ Attempt {attempt+1}/{max_retries}: Selected activator {selected['address'][:10]}... "
                          f"has no capacity (race condition detected), retrying...")
                    # Force refresh and retry
                    continue  # Retry loop
            except Exception as e:
                print(f"⚠️ Attempt {attempt+1}/{max_retries}: Failed to validate capacity for "
                      f"{selected['address'][:10]}...: {e}, retrying...")
                continue  # Retry loop
            
            # Capacity validated successfully
            print(f"✅ Validated: Gen {lowest_gen}, {selected['address'][:10]}..., capacity: {actual_capacity}/12")
            
            # 7. Ensure account is ready (funded + roles)
            self.accounts.ensure_funded(activator_account)
            self.accounts.ensure_roles(activator_account, self.contract)
            
            # 8. Mint invite for this activator
            invite_code = self._mint_invite(activator_account)
            
            return (activator_account, invite_code)
        
        # All retries exhausted
        raise RuntimeError(
            f"Failed to find activator with capacity after {max_retries} attempts. "
            f"Network may be fully saturated or corrupted."
        )
    
    def _mint_invite(self, activator_account):
        """Минтит новый invite для activator'а"""
        # Generate unique code
        while True:
            part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            code = f"AMANITA-{part1}-{part2}"
            
            exists = self.contract.functions.inviteCodeExists(code).call()
            if not exists:
                break
        
        # Mint with local signing (supports both Anvil pre-funded and deterministic accounts)
        try:
            # Build transaction
            nonce = self.web3.eth.get_transaction_count(activator_account.address)
            gas_price = self.web3.eth.gas_price
            
            transaction = self.contract.functions.mintInvite(code, 0).build_transaction({
                'from': activator_account.address,
                'nonce': nonce,
                'gasPrice': gas_price,
                'chainId': self.web3.eth.chain_id
            })
            
            # Sign locally
            signed_txn = activator_account.sign_transaction(transaction)
            
            # Send raw transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            self.web3.eth.wait_for_transaction_receipt(tx_hash)
            
            self._minted_count += 1
            print(f"🔷 Minted invite #{self._minted_count}: {code} by {activator_account.address[:10]}...")
            
            return code
            
        except Exception as e:
            raise RuntimeError(f"Failed to mint invite for {activator_account.address}: {e}")
    
    def create_bridge_to_next_generation(
        self,
        bridge_size: int = 3,
        min_gap_size: int = 1
    ):
        """
        Создает мост к следующему поколению через резервные щели.
        
        Алгоритм:
        1. Находит резервные щели (capacity >= min_gap_size)
        2. Взять первые bridge_size щелей
        3. Для каждой щели:
           a. Получить аккаунт активатора
           b. Убедиться в наличии ролей
           c. Заминтить инвайт
           d. Создать нового пользователя
           e. Активировать его
           f. Предоставить роли новому активатору
           g. Заминтить инвайт для нового активатора
        4. Вернуть список (new_activator_account, invite_code)
        
        Args:
            bridge_size: Количество новых активаторов для создания (default: 3)
            min_gap_size: Минимальная capacity для использования как щели (default: 1)
        
        Returns:
            List[Tuple[Account, str]]: List of (new_activator_account, invite_code) для новых активаторов
        
        Raises:
            RuntimeError: Если нет достаточного количества щелей для создания моста
        """
        print(f"🌉 Creating bridge to next generation (bridge_size={bridge_size}, min_gap_size={min_gap_size})...")
        
        # 1. Найти резервные щели
        gaps = self.tracker.find_bridge_gaps(min_gap_size=min_gap_size, max_gaps=bridge_size)
        
        if len(gaps) < bridge_size:
            raise RuntimeError(
                f"Insufficient bridge gaps: found {len(gaps)}, needed {bridge_size}. "
                f"Network may be fully saturated or gaps too small (min={min_gap_size})."
            )
        
        # 2. Создать новых активаторов через щели
        new_activators = []
        
        for i, gap in enumerate(gaps[:bridge_size]):
            print(f"🌉 Bridge gap {i+1}/{bridge_size}: Gen {gap['generation']}, "
                  f"{gap['address'][:10]}..., capacity={gap['capacity']}/12")
            
            # 2a. Получить аккаунт активатора с щелью
            gap_activator = self.accounts.get_account_by_address(gap['address'])
            self.accounts.ensure_funded(gap_activator)
            self.accounts.ensure_roles(gap_activator, self.contract)
            
            # 2b. Заминтить инвайт
            invite_code = self._mint_invite(gap_activator)
            
            # 2c. Создать нового пользователя
            new_user_account = self.web3.eth.account.create()
            self.accounts.ensure_funded(new_user_account)
            
            # 2d. Генерировать 12 новых инвайтов для нового пользователя
            new_invites = []
            for j in range(12):
                # Используем тот же формат что и _mint_invite для консистентности
                while True:
                    part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                    part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                    code = f"AMANITA-{part1}-{part2}"
                    
                    # Проверяем уникальность
                    exists = self.contract.functions.inviteCodeExists(code).call()
                    if not exists:
                        # Проверяем что нет в уже сгенерированных
                        if code not in new_invites:
                            new_invites.append(code)
                            break
            
            # 2e. Активировать нового пользователя
            try:
                # Build transaction
                nonce = self.web3.eth.get_transaction_count(gap_activator.address)
                gas_price = self.web3.eth.gas_price
                
                transaction = self.contract.functions.activateUser(
                    invite_code,
                    new_user_account.address,
                    new_invites,
                    0  # expiry
                ).build_transaction({
                    'from': gap_activator.address,
                    'nonce': nonce,
                    'gasPrice': gas_price,
                    'chainId': self.web3.eth.chain_id
                })
                
                # Sign locally
                signed_txn = gap_activator.sign_transaction(transaction)
                
                # Send raw transaction
                tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt.status != 1:
                    raise RuntimeError(f"Activation transaction failed: receipt.status={receipt.status}")
                
                print(f"✅ Activated new user {new_user_account.address[:10]}... "
                      f"via gap activator {gap_activator.address[:10]}... (tx: {tx_hash.hex()[:10]}...)")
                
            except Exception as e:
                raise RuntimeError(
                    f"Failed to activate user via gap {gap['address'][:10]}...: {e}"
                )
            
            # 2f. Предоставить роли новому активатору
            self.accounts.ensure_roles(new_user_account, self.contract)
            
            # 2g. Заминтить инвайт для нового активатора (для будущего использования)
            new_activator_invite = self._mint_invite(new_user_account)
            
            new_activators.append((new_user_account, new_activator_invite))
            
            print(f"✅ Bridge activator {i+1}/{bridge_size} created: "
                  f"{new_user_account.address[:10]}... (capacity=12/12)")
        
        print(f"🌉 Bridge created: {len(new_activators)} new activators with capacity 12/12")
        
        # 3. Обновить состояние сети
        self.tracker.refresh_state(force=True)
        
        return new_activators


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _auto_fund_deployer(web3):
    """
    Auto-fund deployer in Anvil if balance low.
    
    Anvil doesn't include custom deployer (0x8F6251F6...) in pre-funded accounts.
    This helper automatically funds deployer via Anvil RPC if balance < 10 ETH.
    
    Graceful: Skips if not Anvil or if funding fails (e.g., Hardhat node).
    """
    deployer_address = os.getenv("DEPLOYER_ADDRESS")
    if not deployer_address:
        return  # No deployer configured, skip
    
    try:
        # Check current balance
        balance = web3.eth.get_balance(deployer_address)
        balance_eth = web3.from_wei(balance, 'ether')
        
        if balance_eth < 10:  # Fund if less than 10 ETH
            print(f"💰 Deployer balance low: {balance_eth} ETH")
            print(f"💰 Auto-funding via Anvil RPC...")
            
            # Try Anvil setBalance RPC
            web3.provider.make_request('anvil_setBalance', [
                deployer_address,
                hex(web3.to_wei(100, 'ether'))
            ])
            
            # Verify funding
            new_balance = web3.from_wei(web3.eth.get_balance(deployer_address), 'ether')
            print(f"✅ Deployer funded: {deployer_address[:10]}... = {new_balance} ETH")
        else:
            print(f"✅ Deployer balance sufficient: {deployer_address[:10]}... = {balance_eth} ETH")
    
    except Exception as e:
        # Not Anvil or RPC not supported - graceful skip
        print(f"⚠️  Auto-funding unavailable: {str(e)[:50]}...")
        print(f"⚠️  If using Anvil, fund deployer manually:")
        print(f"     cast rpc anvil_setBalance {deployer_address} 0x56BC75E2D63100000")


# ═══════════════════════════════════════════════════════════════
# PYTEST FIXTURES
# ═══════════════════════════════════════════════════════════════


@pytest.fixture()
def ipfs_factory():
    """
    Изолированный ipfs_factory для интеграционных тестов.
    На каждый тест поднимается отдельное in-memory хранилище.
    """
    # Lazy import to avoid import errors during conftest loading
    from bot.tests.integration.ipfs_stub import IPFSFactoryStub
    return IPFSFactoryStub(storage={})

@pytest.fixture()
def blockchain_service():
    """
    Stub BlockchainService с развёрнутым контрактом AmanitaInternational.
    """
    # Lazy import to avoid import errors during conftest loading
    from bot.tests.integration.blockchain_stub import BlockchainServiceStub
    return BlockchainServiceStub()

@pytest.fixture()
def translation_cache_service(tmp_path):
    """
    Реальный TranslationCacheService с отдельной temp-директорией.
    Persist ipfs.json между вызовами в рамках одного теста.
    """
    cache_dir = tmp_path / "cache" / "translations"
    return TranslationCacheService(cache_dir=str(cache_dir))

@pytest.fixture()
def fallback_service():
    """
    Простой fallback-стаб: метод get_translation_with_fallback возвращает None (не используется в happy-path).
    """
    class _Fallback:
        def get_translation_with_fallback(self, *args, **kwargs):
            return None
    return _Fallback()

@pytest.fixture()
def multilingual_ipfs_service(ipfs_factory, translation_cache_service, fallback_service, blockchain_service):
    """
    Собранный MultilingualIPFSService с blockchain_service, ipfs_factory и реальным TranslationCacheService.
    """
    return MultilingualIPFSService(
        ipfs_factory=ipfs_factory,
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        blockchain_service=blockchain_service,
    )

@pytest.fixture()
def localization_service(multilingual_ipfs_service, translation_cache_service, fallback_service):
    """
    Готовый LocalizationService с DI-зависимостями для интеграционных тестов.
    """
    return LocalizationService(
        lang='en',
        cache_service=translation_cache_service,
        fallback_service=fallback_service,
        ipfs_service=multilingual_ipfs_service,
    )


# ============================================================================
# Реальные фикстуры для интеграционных тестов
# ============================================================================
# Эти фикстуры переопределяют Mock фикстуры из bot/tests/conftest.py
# для использования реального блокчейна в интеграционных тестах

@pytest.fixture(scope="session")
def real_blockchain_service():
    """
    Реальный BlockchainService для интеграционных тестов (паттерн из test_blockchain.py:35-39).
    Session-scoped для network growth infrastructure.
    """
    from bot.services.core.blockchain import BlockchainService
    
    BlockchainService.reset()
    service = BlockchainService()
    
    # Проверяем подключение
    if not service.web3.is_connected():
        pytest.skip("⚠️ Local node недоступен (проверьте, что Anvil/Hardhat node запущен)")
    
    # Auto-fund deployer if Anvil and balance low
    _auto_fund_deployer(service.web3)
    
    return service


@pytest.fixture(scope="session")
def web3(real_blockchain_service):
    """
    Реальный Web3 экземпляр для интеграционных тестов.
    Session-scoped для network growth infrastructure.
    Переопределяет Mock фикстуру из bot/tests/conftest.py.
    """
    return real_blockchain_service.web3


@pytest.fixture(scope="function")
def seller_account():
    """
    Аккаунт продавца из Web3 (паттерн из test_onboarding_integration.py:47-52).
    Переопределяет Mock фикстуру из bot/tests/conftest.py.
    """
    seller_private_key = os.getenv("SELLER_PRIVATE_KEY")
    if not seller_private_key:
        pytest.skip("SELLER_PRIVATE_KEY не найден в .env")
    
    try:
        return Account.from_key(seller_private_key)
    except Exception as e:
        pytest.skip(f"Ошибка создания аккаунта продавца: {e}")


@pytest.fixture(scope="function")
def user_account():
    """
    Тестовый пользовательский аккаунт (создается для каждого теста).
    """
    return Account.create()


@pytest.fixture(scope="function")
def user_accounts():
    """
    Несколько тестовых пользовательских аккаунтов для batch-тестов.
    Возвращает список из 3 аккаунтов.
    """
    return [Account.create() for _ in range(3)]


@pytest.fixture(scope="function")
def registry_contract(real_blockchain_service):
    """
    Контракт MagicRegistry для интеграционных тестов.
    Используется для проверки регистрации контрактов.
    """
    return real_blockchain_service.registry


@pytest.fixture(scope="session")
def spiral_engine_contract(real_blockchain_service):
    """
    Реальный контракт SpiralEngine для интеграционных тестов.
    Session-scoped для network growth infrastructure.
    """
    contract = real_blockchain_service.get_contract("SpiralEngine")
    if not contract:
        pytest.skip("SpiralEngine контракт не найден в блокчейне")
    return contract


@pytest.fixture(scope="session")
def real_component_data():
    """
    Загружает реальные данные компонента из data/components/.
    Возвращает dict с компонентом, который имеет реальные CID.
    
    Returns:
        dict: {
            'component_id': str,
            'state': dict (from _upload_state.json),
            'simple_fields': dict (actual JSON files),
            'complex_fields': dict (actual JSON files by lang),
            'blockchain_id': int (from deployments.localhost or deployments.ganache)
        }
    """
    # Определяем путь к проекту
    project_root = Path(__file__).resolve().parents[3]  # bot/tests/integration -> tests -> bot -> project
    components_dir = project_root / "data" / "components"
    
    # Выбираем первый доступный компонент с полными данными
    available_components = []
    
    for component_dir in components_dir.iterdir():
        if not component_dir.is_dir():
            continue
        
        state_file = component_dir / "_upload_state.json"
        if not state_file.exists():
            continue
        
        # Загружаем state
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        # Проверяем что component registered
        if 'component_registered' not in state.get('arweave', {}).get('steps_completed', []):
            continue
        
        # Проверяем deployment на localhost (Anvil/Hardhat) or ganache (legacy)
        deployments = state.get('deployments', {})
        if 'localhost' in deployments:
            blockchain_id = deployments['localhost'].get('blockchain_id')
        elif 'ganache' in deployments:
            blockchain_id = deployments['ganache'].get('blockchain_id')
        else:
            continue  # No deployment found
        
        blockchain_id = blockchain_id
        if not blockchain_id:
            continue
        
        # Загружаем simple fields
        simple_fields_data = {}
        for field_name, field_info in state.get('arweave', {}).get('simple_fields', {}).items():
            file_path = component_dir / field_info['file_path']
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    simple_fields_data[field_name] = json.load(f)
        
        # Загружаем complex fields
        complex_fields_data = {}
        for lang, field_info in state.get('arweave', {}).get('complex_fields', {}).items():
            file_path = component_dir / field_info['file_path']
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    complex_fields_data[lang] = json.load(f)
        
        available_components.append({
            'component_id': state['biounit_id'],
            'state': state,
            'simple_fields': simple_fields_data,
            'complex_fields': complex_fields_data,
            'blockchain_id': blockchain_id,
            'directory': component_dir
        })
    
    if not available_components:
        pytest.skip("Нет доступных компонентов с полными данными в data/components/")
    
    # Возвращаем первый доступный
    return available_components[0]


@pytest.fixture(scope="function")
def component_with_real_cid(real_component_data, real_blockchain_service):
    """
    Компонент с реальным CID, зарегистрированным в блокчейне.
    Проверяет что CID действительно записан в OrganicComponentRegistry.
    
    Returns:
        dict: {
            'component_id': str,
            'blockchain_id': int,
            'cids': dict (lang -> CID mapping),
            'contract': Contract (OrganicComponentRegistry)
        }
    """
    component_id = real_component_data['component_id']
    blockchain_id = real_component_data['blockchain_id']
    
    # Загружаем контракт OrganicComponentRegistry
    ocr_contract = real_blockchain_service.get_contract("OrganicComponentRegistry")
    if not ocr_contract:
        pytest.skip("OrganicComponentRegistry не найден в блокчейне")
    
    # Проверяем что компонент существует в контракте
    try:
        exists = ocr_contract.functions.componentExists(blockchain_id).call()
        if not exists:
            pytest.skip(f"Компонент {component_id} (ID={blockchain_id}) не найден в контракте")
    except Exception as e:
        pytest.skip(f"Ошибка проверки компонента: {e}")
    
    # Собираем CID mapping из state
    cids = {}
    for lang, field_info in real_component_data['state']['arweave']['complex_fields'].items():
        cids[lang] = field_info['cid']
    
    return {
        'component_id': component_id,
        'blockchain_id': blockchain_id,
        'cids': cids,
        'contract': ocr_contract,
        'full_data': real_component_data
    }


@pytest.fixture(scope="session")
def deployer_account():
    """
    Deployer account (root activator, generation 0).
    Has DEFAULT_ADMIN_ROLE + SELLER_ROLE + ACTIVATOR_ROLE.
    Session scope: один deployer для всей test session.
    """
    deployer_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    if not deployer_key:
        pytest.skip("DEPLOYER_PRIVATE_KEY required")
    
    return Account.from_key(deployer_key)


@pytest.fixture(scope="session")
def network_state_tracker(spiral_engine_contract, web3):
    """
    Session-wide network state tracker.
    Queries on-chain activation graph и detects capacity.
    """
    return NetworkStateTracker(spiral_engine_contract, web3)


@pytest.fixture(scope="session")
def account_manager(web3, deployer_account):
    """
    Session-wide deterministic account manager.
    Creates reproducible accounts для activators.
    """
    return DeterministicAccountManager(web3, deployer_account)


@pytest.fixture(scope="session")
def exponential_activator_pool(network_state_tracker, account_manager, spiral_engine_contract, web3):
    """
    Exponential growth activator pool.
    
    Automatically:
    - Finds activators с capacity
    - Mints invites
    - Grants roles
    - Grows network exponentially (breadth-first)
    
    Works на ЛЮБОМ network state (0 → 1000+ users).
    """
    return ExponentialActivatorPool(
        network_state_tracker,
        account_manager,
        spiral_engine_contract,
        web3
    )


@pytest.fixture(scope="function")
def network_growth_context(exponential_activator_pool, spiral_engine_contract, request):
    """
    Context для network growth tests.
    Provides activator + invite для каждого теста.
    Automatically logs network growth.
    
    Automatically validates capacity перед возвратом для защиты от race conditions.
    Logs network diagnostics before providing activator (once per session).
    """
    # Log network diagnostics (only for first test to avoid spam)
    # Check if diagnostics were already logged in this session using tracker
    if not hasattr(exponential_activator_pool.tracker, '_diagnostics_logged'):
        exponential_activator_pool.tracker.log_network_diagnostics()
        exponential_activator_pool.tracker._diagnostics_logged = True
    
    # Get state before
    state_before = exponential_activator_pool.tracker.refresh_state(force=True)
    
    # Get activator + invite (get_next уже включает валидацию capacity)
    activator, invite = exponential_activator_pool.get_next()
    
    # Дополнительная валидация: проверяем capacity непосредственно перед возвратом
    # Это защищает от race conditions между get_next() и фактическим использованием в тесте
    try:
        circle = spiral_engine_contract.functions.getCircleMembers(activator.address).call()
        capacity = 12 - len(circle)
        if capacity <= 0:
            # Capacity потерян, получаем нового активатора
            print(f"⚠️ Initial activator {activator.address[:10]}... lost capacity, retrying...")
            activator, invite = exponential_activator_pool.get_next()
    except Exception as e:
        print(f"⚠️ Failed to validate initial activator capacity: {e}, continuing anyway...")
    
    context = {
        'activator': activator,
        'invite_code': invite,
        'contract': spiral_engine_contract,
        'pool': exponential_activator_pool,
        'state_before': state_before
    }
    
    yield context
    
    # After test: log growth
    state_after = exponential_activator_pool.tracker.refresh_state(force=True)
    
    growth = state_after['total_users'] - state_before['total_users']
    if growth > 0:
        print(f"📈 Network grew: +{growth} users (total: {state_after['total_users']})")


@pytest.fixture(scope="function")
def fresh_activator(spiral_engine_contract, web3):
    """
    Создаёт новый account с ACTIVATOR_ROLE для тестов.
    Bypasses activator circle limit для deployed seller.
    """
    import os
    
    # Create fresh account
    fresh_account = web3.eth.account.create()
    
    # Grant ACTIVATOR_ROLE using deployer
    deployer_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    if not deployer_key:
        pytest.skip("DEPLOYER_PRIVATE_KEY required for creating fresh activator")
    
    deployer = Account.from_key(deployer_key)
    ACTIVATOR_ROLE = web3.keccak(text="ACTIVATOR_ROLE")
    
    try:
        tx_hash = spiral_engine_contract.functions.grantRole(
            ACTIVATOR_ROLE, fresh_account.address
        ).transact({'from': deployer.address})
        web3.eth.wait_for_transaction_receipt(tx_hash)
    except Exception as e:
        pytest.skip(f"Cannot grant ACTIVATOR_ROLE to fresh account: {e}")
    
    return fresh_account


@pytest.fixture(scope="session", autouse=True)
def export_network_after_suite(spiral_engine_contract):
    """
    Auto-export network graph после всех integration tests.
    Creates activation_graph.json with full network state.
    """
    yield  # Tests run
    
    # After all tests complete
    try:
        from bot.tests.utils.network_exporter import NetworkExporter
        
        exporter = NetworkExporter(spiral_engine_contract)
        output_file = exporter.export_graph()
        
        # Get and print final stats
        stats = exporter.get_network_stats()
        
        print("\n" + "="*70)
        print("📊 FINAL NETWORK STATE (Organic Trust Communities)")
        print("="*70)
        print(f"📍 Total Nodes: {stats['total_nodes']}")
        print(f"🔗 Total Edges: {stats['total_edges']}")
        print(f"📶 Max Generation: {stats['max_generation']}")
        print(f"👥 Communities: {stats['communities']} organic trust communities")
        print(f"🌱 Gen 1 Size: {stats['gen1_size']}/12")
        print(f"📁 Graph File: {output_file}")
        print("="*70)
        print("💡 Use this graph for:")
        print("   - D3.js visualization")
        print("   - NetworkX analytics")
        print("   - DAO/Circles planning")
        print("   - Токеномика simulation")
        print("="*70)
        
    except Exception as e:
        print(f"⚠️  Failed to export network graph: {e}")


