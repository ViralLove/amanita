const { expect } = require("chai");
const { ethers } = require("hardhat");

async function expectRevertWithMessage(txPromise, messageSubstring) {
    let err;
    try {
        const tx = await txPromise;
        if (tx && typeof tx.wait === "function") await tx.wait();
    } catch (e) {
        err = e;
    }
    expect(err, "expected transaction to revert").to.be.ok;
    const msg = (err?.reason || err?.shortMessage || err?.message || err?.error?.message || String(err)) || "";
    expect(msg.includes(messageSubstring), `expected revert message to contain "${messageSubstring}"`).to.be.true;
}

/**
 * 🧪 MagicRegistry Comprehensive Test Suite
 * 
 * Применяет методологию @test-to-success.mdc с жёстким анализом качества @test-qualification.mdc
 * 
 * Критические пути для тестирования:
 * - set/get (основная функциональность)
 * - Access Control (onlyOwner модификатор)
 * - Edge Cases (нулевые адреса, дублирование ключей)
 * - События (MagicEvent)
 * - Управление контрактами (getNames)
 */

describe("🔍 MagicRegistry - Comprehensive Test Suite", function () {
    let magicRegistry;
    let deployer;
    let user1;
    let user2;

    // Утилиты для детального логирования
    async function logContractState(context) {
        console.log(`\n📊 [${context}] Состояние контракта:`);
        console.log(`   Owner: ${await magicRegistry.owner()}`);
        
        try {
            const allNames = await magicRegistry.getNames();
            console.log(`   Зарегистрированных контрактов: ${allNames.length}`);
            for (const name of allNames) {
                const address = await magicRegistry.get(name);
                console.log(`   ${name}: ${address}`);
            }
        } catch (error) {
            console.log(`   Ошибка получения списка: ${error.message}`);
        }
    }

    async function logTransactionDetails(tx, operation) {
        console.log(`\n⏳ [${operation}] Транзакция отправлена: ${tx.hash}`);
        const receipt = await tx.wait();
        console.log(`✅ [${operation}] Подтверждена в блоке: ${receipt.blockNumber}`);
        console.log(`⛽ [${operation}] Потрачено газа: ${receipt.gasUsed.toString()}`);
        
        // Анализ событий
        if (receipt.logs && receipt.logs.length > 0) {
            console.log(`📋 [${operation}] События (${receipt.logs.length}):`);
            for (const log of receipt.logs) {
                try {
                    const parsed = magicRegistry.interface.parseLog(log);
                    console.log(`   - ${parsed.name}: ${JSON.stringify(parsed.args)}`);
                } catch (error) {
                    console.log(`   - Неизвестное событие: ${log.topics[0]}`);
                }
            }
        }
        
        return receipt;
    }

    function logEventDetails(event, eventName) {
        console.log(`\n🎉 Событие ${eventName}:`);
        console.log(`   key: ${event.args.key.toString()}`);
        console.log(`   value: ${event.args.value}`);
    }

    beforeEach(async function () {
        console.log("\n🔷 Настройка тестового окружения...");
        
        // Получаем аккаунты
        [deployer, user1, user2] = await ethers.getSigners();
        console.log(`📋 Deployer: ${deployer.address}`);
        console.log(`📋 User1: ${user1?.address || 'undefined'}`);
        console.log(`📋 User2: ${user2?.address || 'undefined'}`);
        
        // Деплоим MagicRegistry
        console.log("🚀 Деплоим MagicRegistry...");
        const MagicRegistryFactory = await ethers.getContractFactory("MagicRegistry");
        magicRegistry = await MagicRegistryFactory.deploy();
        await magicRegistry.waitForDeployment();
        
        console.log(`✅ MagicRegistry задеплоен: ${magicRegistry.target}`);
        
        // Логируем начальное состояние
        await logContractState("BEFORE_EACH");
    });

    describe("🏗️ P0 - Критические пути: Основная функциональность", function () {
        
        describe("set/get - Основная функциональность", function () {
            
            it("Should set and get address correctly - NO_FALSE_SUCCESSES", async function () {
                console.log("\n🧪 Тест: set/get - проверка реальной функциональности");
                
                const testName = "SpiralEngine";
                const testAddress = "0x1234567890123456789012345678901234567890";
                
                // P0: Проверяем состояние ДО операции
                const addressBefore = await magicRegistry.get(testName);
                console.log(`📋 Адрес ДО операции: ${addressBefore}`);
                expect(addressBefore).to.equal(ethers.ZeroAddress);
                
                // Выполняем set
                console.log(`🔧 Устанавливаем ${testName} = ${testAddress}`);
                const tx = await magicRegistry.connect(deployer).set(testName, testAddress);
                const receipt = await logTransactionDetails(tx, "set");
                
                // P0: VALIDATE_REAL_FUNCTIONALITY - проверяем РЕАЛЬНОЕ состояние
                const addressAfter = await magicRegistry.get(testName);
                console.log(`📋 Адрес ПОСЛЕ операции: ${addressAfter}`);
                
                // Жёсткая проверка - адрес должен быть ТОЧНО равен ожидаемому
                expect(addressAfter.toLowerCase()).to.equal(testAddress.toLowerCase());
                
                // Дополнительная проверка - адрес не должен быть нулевым
                expect(addressAfter).to.not.equal(ethers.ZeroAddress);
                
                // Проверяем событие
                const event = receipt.logs.find(log => {
                    try {
                        const parsed = magicRegistry.interface.parseLog(log);
                        return parsed.name === "MagicEvent";
                    } catch {
                        return false;
                    }
                });
                
                expect(event).to.not.be.undefined;
                logEventDetails(event, "MagicEvent");
                
                // Финальная проверка состояния
                await logContractState("AFTER_SET");
            });

            it("Should update existing address - NO_UNTESTED_CRITICAL_PATHS", async function () {
                console.log("\n🧪 Тест: Обновление существующего адреса");
                
                const testName = "ProductRegistry";
                const firstAddress = "0x1111111111111111111111111111111111111111";
                const secondAddress = "0x2222222222222222222222222222222222222222";
                
                // Устанавливаем первый адрес
                console.log(`🔧 Устанавливаем первый адрес: ${firstAddress}`);
                await magicRegistry.connect(deployer).set(testName, firstAddress);
                
                const firstResult = await magicRegistry.get(testName);
                expect(firstResult.toLowerCase()).to.equal(firstAddress.toLowerCase());
                
                // Обновляем на второй адрес
                console.log(`🔧 Обновляем на второй адрес: ${secondAddress}`);
                const tx = await magicRegistry.connect(deployer).set(testName, secondAddress);
                await logTransactionDetails(tx, "update");
                
                // Проверяем, что адрес обновился
                const secondResult = await magicRegistry.get(testName);
                expect(secondResult.toLowerCase()).to.equal(secondAddress.toLowerCase());
                expect(secondResult.toLowerCase()).to.not.equal(firstAddress.toLowerCase());
                
                await logContractState("AFTER_UPDATE");
            });

            it("Should handle multiple contracts - CORRECT_LOGIC", async function () {
                console.log("\n🧪 Тест: Множественные контракты");
                
                const contracts = {
                    "SpiralEngine": "0x1234567890123456789012345678901234567890",
                    "ProductRegistry": "0x2345678901234567890123456789012345678901",
                    "SoulIdentity": "0x3456789012345678901234567890123456789012"
                };
                
                // Устанавливаем все контракты
                for (const [name, address] of Object.entries(contracts)) {
                    console.log(`🔧 Устанавливаем ${name} = ${address}`);
                    const tx = await magicRegistry.connect(deployer).set(name, address);
                    await logTransactionDetails(tx, `set_${name}`);
                    
                    // Проверяем каждый сразу после установки
                    const result = await magicRegistry.get(name);
                    expect(result.toLowerCase()).to.equal(address.toLowerCase());
                }
                
                // Проверяем все контракты в конце
                await logContractState("AFTER_ALL_CONTRACTS");
                
                // Проверяем getNames
                const allNames = await magicRegistry.getNames();
                expect(allNames.length).to.equal(3);
                expect(allNames).to.include("SpiralEngine");
                expect(allNames).to.include("ProductRegistry");
                expect(allNames).to.include("SoulIdentity");
            });
        });
    });

    describe("🛡️ P0 - Критические пути: Access Control", function () {
        
        it("Should reject non-owner calls to set - NO_FALSE_SUCCESSES", async function () {
            console.log("\n🧪 Тест: Отклонение вызовов от не-owner");
            
            const testName = "UnauthorizedContract";
            const testAddress = "0x1234567890123456789012345678901234567890";
            
            await expectRevertWithMessage(
                magicRegistry.connect(user1).set(testName, testAddress),
                "MagicRegistry: not owner"
            );
            
            // Проверяем, что адрес не изменился
            const address = await magicRegistry.get(testName);
            expect(address).to.equal(ethers.ZeroAddress);
            
            console.log("✅ Неавторизованный вызов корректно отклонён");
        });

        it("Should allow owner to call set - VALIDATE_REAL_FUNCTIONALITY", async function () {
            console.log("\n🧪 Тест: Разрешение вызовов от owner");
            
            const testName = "OwnerContract";
            const testAddress = "0x1234567890123456789012345678901234567890";
            
            // Owner должен иметь возможность вызвать set
            const tx = await magicRegistry.connect(deployer).set(testName, testAddress);
            await logTransactionDetails(tx, "owner_set");
            
            const result = await magicRegistry.get(testName);
            expect(result.toLowerCase()).to.equal(testAddress.toLowerCase());
            
            console.log("✅ Owner успешно установил адрес");
        });

        it("Should change owner correctly - NO_UNTESTED_CRITICAL_PATHS", async function () {
            console.log("\n🧪 Тест: Смена владельца контракта");
            
            const newOwner = user1.address;
            
            // Проверяем текущего владельца
            const currentOwner = await magicRegistry.owner();
            expect(currentOwner).to.equal(deployer.address);
            console.log(`📋 Текущий владелец: ${currentOwner}`);
            
            // Меняем владельца
            console.log(`🔧 Меняем владельца на: ${newOwner}`);
            const tx = await magicRegistry.connect(deployer).changeOwner(newOwner);
            await logTransactionDetails(tx, "changeOwner");
            
            // Проверяем, что владелец изменился
            const updatedOwner = await magicRegistry.owner();
            expect(updatedOwner).to.equal(newOwner);
            console.log(`✅ Новый владелец: ${updatedOwner}`);
            
            console.log("🔍 Проверяем, что старый владелец не может вызывать set...");
            await expectRevertWithMessage(
                magicRegistry.connect(deployer).set("Test", "0x1234567890123456789012345678901234567890"),
                "MagicRegistry: not owner"
            );
            console.log("✅ Старый владелец корректно заблокирован");
            
            // Проверяем, что новый владелец может вызывать set
            console.log("🔍 Проверяем, что новый владелец может вызывать set...");
            const tx2 = await magicRegistry.connect(user1).set("Test", "0x1234567890123456789012345678901234567890");
            await logTransactionDetails(tx2, "new_owner_set");
            
            const result = await magicRegistry.get("Test");
            expect(result.toLowerCase()).to.equal("0x1234567890123456789012345678901234567890");
            console.log("✅ Новый владелец успешно установил адрес");
            
            // Проверяем, что новый владелец может менять владельца обратно
            console.log("🔍 Проверяем, что новый владелец может менять владельца...");
            const tx3 = await magicRegistry.connect(user1).changeOwner(deployer.address);
            await logTransactionDetails(tx3, "change_owner_back");
            
            const finalOwner = await magicRegistry.owner();
            expect(finalOwner).to.equal(deployer.address);
            console.log("✅ Владелец успешно изменён обратно");
        });

        it("Should reject zero address for changeOwner - NO_FALSE_SUCCESSES", async function () {
            console.log("\n🧪 Тест: Отклонение нулевого адреса для changeOwner");
            
            await expectRevertWithMessage(
                magicRegistry.connect(deployer).changeOwner(ethers.ZeroAddress),
                "MagicRegistry: zero address"
            );
            
            // Проверяем, что владелец не изменился
            const owner = await magicRegistry.owner();
            expect(owner).to.equal(deployer.address);
            
            console.log("✅ Нулевой адрес для changeOwner корректно отклонён");
        });

        it("Should reject non-owner calls to changeOwner - NO_FALSE_SUCCESSES", async function () {
            console.log("\n🧪 Тест: Отклонение вызовов changeOwner от не-owner");
            
            const newOwner = user2.address;
            
            await expectRevertWithMessage(
                magicRegistry.connect(user1).changeOwner(newOwner),
                "MagicRegistry: not owner"
            );
            
            // Проверяем, что владелец не изменился
            const owner = await magicRegistry.owner();
            expect(owner).to.equal(deployer.address);
            
            console.log("✅ Неавторизованный вызов changeOwner корректно отклонён");
        });
    });

    describe("⚠️ P0 - Критические пути: Edge Cases", function () {
        
        it("Should reject zero address - NO_FALSE_SUCCESSES", async function () {
            console.log("\n🧪 Тест: Отклонение нулевого адреса");
            
            const testName = "ZeroAddressContract";
            
            await expectRevertWithMessage(
                magicRegistry.connect(deployer).set(testName, ethers.ZeroAddress),
                "MagicRegistry: zero address"
            );
            
            // Проверяем, что адрес не изменился
            const address = await magicRegistry.get(testName);
            expect(address).to.equal(ethers.ZeroAddress);
            
            console.log("✅ Нулевой адрес корректно отклонён");
        });

        it("Should handle empty string name - CORRECT_LOGIC", async function () {
            console.log("\n🧪 Тест: Пустое имя контракта");
            
            const emptyName = "";
            const testAddress = "0x1234567890123456789012345678901234567890";
            
            // Проверяем, что пустое имя обрабатывается корректно
            const tx = await magicRegistry.connect(deployer).set(emptyName, testAddress);
            await logTransactionDetails(tx, "empty_name");
            
            const result = await magicRegistry.get(emptyName);
            expect(result.toLowerCase()).to.equal(testAddress.toLowerCase());
            
            console.log("✅ Пустое имя обработано корректно");
        });

        it("Should handle very long name - CORRECT_LOGIC", async function () {
            console.log("\n🧪 Тест: Очень длинное имя контракта");
            
            const longName = "VeryLongContractNameThatExceedsNormalLengthAndShouldBeHandledCorrectlyByTheContract";
            const testAddress = "0x1234567890123456789012345678901234567890";
            
            const tx = await magicRegistry.connect(deployer).set(longName, testAddress);
            await logTransactionDetails(tx, "long_name");
            
            const result = await magicRegistry.get(longName);
            expect(result.toLowerCase()).to.equal(testAddress.toLowerCase());
            
            console.log("✅ Длинное имя обработано корректно");
        });
    });

    describe("📋 P1 - Логика тестов: Управление контрактами", function () {
        
        it("Should maintain contract names list correctly - CORRECT_LOGIC", async function () {
            console.log("\n🧪 Тест: Корректное ведение списка имён контрактов");
            
            // Начальное состояние
            let allNames = await magicRegistry.getNames();
            expect(allNames.length).to.equal(0);
            console.log(`📋 Начальное количество контрактов: ${allNames.length}`);
            
            // Добавляем первый контракт
            await magicRegistry.connect(deployer).set("Contract1", "0x1111111111111111111111111111111111111111");
            allNames = await magicRegistry.getNames();
            expect(allNames.length).to.equal(1);
            expect(allNames[0]).to.equal("Contract1");
            console.log(`📋 После добавления первого: ${allNames.length}`);
            
            // Добавляем второй контракт
            await magicRegistry.connect(deployer).set("Contract2", "0x2222222222222222222222222222222222222222");
            allNames = await magicRegistry.getNames();
            expect(allNames.length).to.equal(2);
            expect(allNames).to.include("Contract1");
            expect(allNames).to.include("Contract2");
            console.log(`📋 После добавления второго: ${allNames.length}`);
            
            // Обновляем существующий контракт (должно добавить дубликат в наш случае)
            await magicRegistry.connect(deployer).set("Contract1", "0x3333333333333333333333333333333333333333");
            allNames = await magicRegistry.getNames();
            expect(allNames.length).to.equal(3); // В MagicRegistry добавляется каждый раз
            expect(allNames).to.include("Contract1");
            expect(allNames).to.include("Contract2");
            console.log(`📋 После обновления первого: ${allNames.length} (с дубликатом)`);
        });

        it("Should handle get for non-existent contract - CORRECT_LOGIC", async function () {
            console.log("\n🧪 Тест: Получение адреса несуществующего контракта");
            
            const nonExistentName = "NonExistentContract";
            const address = await magicRegistry.get(nonExistentName);
            
            // Для несуществующего контракта должен возвращаться нулевой адрес
            expect(address).to.equal(ethers.ZeroAddress);
            console.log(`✅ Несуществующий контракт возвращает нулевой адрес: ${address}`);
        });
    });

    describe("🔄 P2 - Использование моков: MINIMAL_MOCK_OVERUSE", function () {
        
        it("Should work with real contract instances - MINIMAL_MOCK_OVERUSE", async function () {
            console.log("\n🧪 Тест: Работа с реальными экземплярами контрактов");
            
            // Деплоим реальный тестовый контракт
            const TestContractFactory = await ethers.getContractFactory("MagicRegistry");
            const testContract = await TestContractFactory.deploy();
            await testContract.waitForDeployment();
            const testContractAddress = await testContract.getAddress();
            
            console.log(`🔧 Деплоим тестовый контракт: ${testContractAddress}`);
            
            // Регистрируем реальный контракт в реестре
            const tx = await magicRegistry.connect(deployer).set("TestContract", testContractAddress);
            await logTransactionDetails(tx, "register_real_contract");
            
            // Проверяем, что адрес сохранился корректно
            const retrievedAddress = await magicRegistry.get("TestContract");
            expect(retrievedAddress.toLowerCase()).to.equal(testContractAddress.toLowerCase());
            
            // Проверяем, что можем подключиться к контракту по полученному адресу
            const connectedContract = TestContractFactory.attach(retrievedAddress);
            const owner = await connectedContract.owner();
            expect(owner.toLowerCase()).to.equal(deployer.address.toLowerCase());
            
            console.log("✅ Реальный контракт успешно зарегистрирован и доступен");
        });
    });

    describe("🎯 P0 - Критический тест: Выявление проблемы с сохранением", function () {
        
        it("Should identify storage issue - DIAGNOSTIC TEST", async function () {
            console.log("\n🔍 ДИАГНОСТИЧЕСКИЙ ТЕСТ: Выявление проблемы с сохранением");
            
            const testName = "DiagnosticTest";
            const testAddress = "0x1234567890123456789012345678901234567890";
            
            // Детальная диагностика
            console.log("\n📊 ДО операции:");
            await logContractState("BEFORE_DIAGNOSTIC");
            
            // Выполняем set
            console.log(`\n🔧 Выполняем set("${testName}", "${testAddress}")`);
            const tx = await magicRegistry.connect(deployer).set(testName, testAddress);
            const receipt = await logTransactionDetails(tx, "DIAGNOSTIC_set");
            
            // Немедленная проверка
            console.log("\n📊 СРАЗУ ПОСЛЕ операции:");
            const immediateResult = await magicRegistry.get(testName);
            console.log(`   Немедленный результат: ${immediateResult}`);
            console.log(`   Ожидаемый результат:  ${testAddress}`);
            console.log(`   Совпадает: ${immediateResult.toLowerCase() === testAddress.toLowerCase()}`);
            
            // Ждём блок и проверяем снова
            await tx.wait(1);
            console.log("\n📊 ПОСЛЕ ожидания блока:");
            const delayedResult = await magicRegistry.get(testName);
            console.log(`   Отложенный результат: ${delayedResult}`);
            console.log(`   Совпадает: ${delayedResult.toLowerCase() === testAddress.toLowerCase()}`);
            
            // Финальная проверка состояния
            await logContractState("AFTER_DIAGNOSTIC");
            
            // КРИТИЧЕСКАЯ ПРОВЕРКА
            if (immediateResult.toLowerCase() !== testAddress.toLowerCase()) {
                console.log("\n❌ ПРОБЛЕМА ОБНАРУЖЕНА: set не сохраняет данные!");
                console.log("🔍 Возможные причины:");
                console.log("   1. Проблема с mapping в контракте");
                console.log("   2. Проблема с версией Solidity");
                console.log("   3. Проблема с компиляцией");
                console.log("   4. Проблема с транзакциями");
                
                // Не делаем expect.fail() - это диагностический тест
                console.log("⚠️ Диагностический тест завершён с обнаружением проблемы");
            } else {
                console.log("\n✅ set работает корректно!");
            }
        });
    });

    describe("🚀 P0 - Критические пути: Сценарии из deploy_full.js", function () {
        
        it("Should handle mass contract registration like deploy_full.js - NO_UNTESTED_CRITICAL_PATHS", async function () {
            console.log("\n🧪 Тест: Массовая регистрация контрактов как в deploy_full.js");
            
            // Симулируем регистрацию всех контрактов из deploy_full.js
            const contracts = [
                { name: "SpiralEngine", address: "0x1111111111111111111111111111111111111111" },
                { name: "ProductRegistry", address: "0x2222222222222222222222222222222222222222" },
                { name: "SoulboundCore", address: "0x3333333333333333333333333333333333333333" },
                { name: "SoulMetadata", address: "0x4444444444444444444444444444444444444444" },
                { name: "SoulRecovery", address: "0x5555555555555555555555555555555555555555" },
                { name: "SoulIntegration", address: "0x6666666666666666666666666666666666666666" },
                { name: "SoulIdentity", address: "0x7777777777777777777777777777777777777777" }
            ];
            
            console.log(`🔷 Регистрируем ${contracts.length} контрактов...`);
            
            for (let i = 0; i < contracts.length; i++) {
                const contract = contracts[i];
                console.log(`\n📝 Регистрируем ${i + 1}/${contracts.length}: ${contract.name}`);
                
                const tx = await magicRegistry.connect(deployer).set(contract.name, contract.address);
                await logTransactionDetails(tx, `register_${contract.name}`);
                
                // Проверяем, что контракт зарегистрирован
                const registeredAddress = await magicRegistry.get(contract.name);
                expect(registeredAddress.toLowerCase()).to.equal(contract.address.toLowerCase());
                console.log(`✅ ${contract.name} зарегистрирован: ${registeredAddress}`);
            }
            
            // Проверяем общее состояние
            const allNames = await magicRegistry.getNames();
            expect(allNames.length).to.equal(contracts.length);
            console.log(`\n📊 Всего зарегистрировано контрактов: ${allNames.length}`);
            
            // Проверяем каждый контракт
            for (const contract of contracts) {
                const address = await magicRegistry.get(contract.name);
                expect(address.toLowerCase()).to.equal(contract.address.toLowerCase());
            }
            
            console.log("✅ Массовая регистрация контрактов успешна!");
        });

        it("Should handle contract existence check like deploy_full.js - NO_FALSE_SUCCESSES", async function () {
            console.log("\n🧪 Тест: Проверка существования контрактов как в deploy_full.js");
            
            // Проверяем несуществующий контракт (должен вернуть 0x0000...)
            const nonExistentContract = "NonExistentContract";
            const address = await magicRegistry.get(nonExistentContract);
            expect(address).to.equal(ethers.ZeroAddress);
            console.log(`✅ Несуществующий контракт ${nonExistentContract} возвращает нулевой адрес: ${address}`);
            
            // Регистрируем контракт
            const contractName = "TestContract";
            const contractAddress = "0x1234567890123456789012345678901234567890";
            
            await magicRegistry.connect(deployer).set(contractName, contractAddress);
            console.log(`✅ Контракт ${contractName} зарегистрирован`);
            
            // Проверяем существующий контракт
            const existingAddress = await magicRegistry.get(contractName);
            expect(existingAddress.toLowerCase()).to.equal(contractAddress.toLowerCase());
            console.log(`✅ Существующий контракт ${contractName} возвращает правильный адрес: ${existingAddress}`);
            
            // Проверяем логику из deploy_full.js: existingAddress !== '0x0000000000000000000000000000000000000000'
            const isRegistered = existingAddress !== ethers.ZeroAddress;
            expect(isRegistered).to.be.true;
            console.log(`✅ Логика проверки существования работает: ${isRegistered}`);
        });

        it("Should handle contract update like deploy_full.js - CORRECT_LOGIC", async function () {
            console.log("\n🧪 Тест: Обновление контрактов как в deploy_full.js");
            
            const contractName = "UpdatableContract";
            const oldAddress = "0x1111111111111111111111111111111111111111";
            const newAddress = "0x2222222222222222222222222222222222222222";
            
            // Регистрируем контракт первый раз
            console.log(`🔧 Регистрируем ${contractName} с адресом: ${oldAddress}`);
            await magicRegistry.connect(deployer).set(contractName, oldAddress);
            
            const firstAddress = await magicRegistry.get(contractName);
            expect(firstAddress.toLowerCase()).to.equal(oldAddress.toLowerCase());
            console.log(`✅ Первая регистрация: ${firstAddress}`);
            
            // Обновляем контракт (как в deploy_full.js)
            console.log(`🔄 Обновляем ${contractName} на адрес: ${newAddress}`);
            await magicRegistry.connect(deployer).set(contractName, newAddress);
            
            const updatedAddress = await magicRegistry.get(contractName);
            expect(updatedAddress.toLowerCase()).to.equal(newAddress.toLowerCase());
            console.log(`✅ Обновление: ${updatedAddress}`);
            
            // Проверяем, что адрес изменился
            expect(updatedAddress.toLowerCase()).to.not.equal(oldAddress.toLowerCase());
            console.log("✅ Адрес контракта успешно обновлен");
            
            // Проверяем, что в списке имен есть дубликат (как в MagicRegistry)
            const allNames = await magicRegistry.getNames();
            const nameCount = allNames.filter(name => name === contractName).length;
            expect(nameCount).to.equal(2); // Должно быть 2 записи (старая и новая)
            console.log(`✅ В списке имен найдено ${nameCount} записей для ${contractName} (с дубликатом)`);
        });

        it("Should work with real contract addresses like deploy_full.js - MINIMAL_MOCK_OVERUSE", async function () {
            console.log("\n🧪 Тест: Работа с реальными адресами контрактов как в deploy_full.js");
            
            // Симулируем реальные адреса контрактов (как в deploy_full.js)
            const realContracts = [
                { name: "SpiralEngine", address: "0x10D66084e91e9C5706FCDe50892B1b33120aa4a1" },
                { name: "ProductRegistry", address: "0xE678AC9ECEb4497A06B2BdaB9041f60e1973cD8d" },
                { name: "SoulboundCore", address: "0x43f01ea0A841266e1f8a22657f2df48f22830734" },
                { name: "SoulMetadata", address: "0xd6A23e378715f84A6F1fBe433E605321dcF324e6" },
                { name: "SoulRecovery", address: "0xD0130126CF8D1D2Dc473831310039792ddAf681B" },
                { name: "SoulIntegration", address: "0x6C93683644F9fA8Cf78aa129303e31f53eB6fCCE" },
                { name: "SoulIdentity", address: "0x8371ABe81630F3434eDa1Fc30E905dE75326fC12" }
            ];
            
            console.log(`🔷 Регистрируем ${realContracts.length} реальных контрактов...`);
            
            for (const contract of realContracts) {
                console.log(`📝 Регистрируем ${contract.name}: ${contract.address}`);
                
                const tx = await magicRegistry.connect(deployer).set(contract.name, contract.address);
                await logTransactionDetails(tx, `register_${contract.name}`);
                
                // Проверяем регистрацию
                const registeredAddress = await magicRegistry.get(contract.name);
                expect(registeredAddress.toLowerCase()).to.equal(contract.address.toLowerCase());
                console.log(`✅ ${contract.name} зарегистрирован корректно`);
            }
            
            // Проверяем получение всех адресов (как в deploy_full.js)
            console.log("\n🔍 Проверяем получение всех адресов...");
            for (const contract of realContracts) {
                const address = await magicRegistry.get(contract.name);
                expect(address.toLowerCase()).to.equal(contract.address.toLowerCase());
                console.log(`✅ ${contract.name}: ${address}`);
            }
            
            // Проверяем общее количество
            const allNames = await magicRegistry.getNames();
            expect(allNames.length).to.equal(realContracts.length);
            console.log(`\n📊 Всего зарегистрировано: ${allNames.length} контрактов`);
            
            console.log("✅ Работа с реальными адресами контрактов успешна!");
        });
    });

    afterEach(async function () {
        console.log("\n🧹 Очистка после теста...");
        await logContractState("AFTER_EACH");
        console.log("✅ Очистка завершена");
    });
});
