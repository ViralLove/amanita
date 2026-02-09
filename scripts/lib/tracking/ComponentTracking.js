/**
 * ComponentTracking - Централизованный модуль трассировки компонентов
 * 
 * Управляет всеми полями трассировки:
 * - created_by
 * - contributors[]
 * - metadata.validation.validator
 * - change_history[]
 * - moderation.moderated_by
 * - sharing.shared_by
 * 
 * @version 1.0.0
 * @date 2025-01-XX
 */

class ComponentTracking {
  /**
   * Конструктор
   * @param {Object} config - Конфигурация
   * @param {string} config.testAddress - Тестовый адрес для замены (default: '0x1234567890abcdef1234567890abcdef12345678')
   * @param {string} config.zeroAddress - Нулевой адрес (default: '0x0000000000000000000000000000000000000000')
   */
  constructor(config = {}) {
    this.testAddress = config.testAddress || '0x1234567890abcdef1234567890abcdef12345678';
    this.zeroAddress = config.zeroAddress || '0x0000000000000000000000000000000000000000';
  }

  /**
   * Проверка, является ли адрес тестовым/placeholder
   * @param {string} address - Ethereum address
   * @returns {boolean}
   */
  isTestAddress(address) {
    if (!address) return true;
    return address === this.testAddress || address === this.zeroAddress;
  }

  /**
   * Проверка наличия контрибьютора в списке
   * @param {Object} componentData - Данные компонента
   * @param {string} address - Адрес для проверки
   * @returns {boolean}
   */
  hasContributor(componentData, address) {
    if (!componentData.contributors || !Array.isArray(componentData.contributors)) {
      return false;
    }
    return componentData.contributors.some(c => c.address && c.address.toLowerCase() === address.toLowerCase());
  }

  /**
   * Обновить created_by и contributors
   * @param {Object} componentData - Данные компонента
   * @param {string} actorAddress - Адрес создателя
   * @returns {Object} Обновленные данные компонента
   */
  updateOwnership(componentData, actorAddress) {
    const updated = { ...componentData };
    const timestamp = new Date().toISOString();
    
    // 1. Обновить created_by (если тестовый или пустой)
    if (this.isTestAddress(updated.created_by) || !updated.created_by) {
      updated.created_by = actorAddress;
    }
    
    // 2. Обновить contributors (если только тестовые адреса)
    const hasRealContributor = (updated.contributors || []).some(
      c => c.address && !this.isTestAddress(c.address)
    );
    
    if (!hasRealContributor) {
      updated.contributors = [{
        address: actorAddress,
        role: 'creator',
        added_at: timestamp
      }];
    } else {
      // Добавить новый адрес в contributors, если его еще нет
      if (!this.hasContributor(updated, actorAddress)) {
        updated.contributors = [
          ...(updated.contributors || []),
          {
            address: actorAddress,
            role: 'contributor',
            added_at: timestamp
          }
        ];
      }
    }
    
    return updated;
  }

  /**
   * Обновить validator в metadata.validation
   * @param {Object} componentData - Данные компонента
   * @param {string} validatorAddress - Адрес валидатора
   * @returns {Object} Обновленные данные компонента
   */
  updateValidator(componentData, validatorAddress) {
    const updated = { ...componentData };
    
    if (!updated.metadata) {
      updated.metadata = {};
    }
    if (!updated.metadata.validation) {
      updated.metadata.validation = {};
    }
    
    updated.metadata.validation.validator = validatorAddress;
    updated.metadata.validation.last_validated = new Date().toISOString();
    
    return updated;
  }

  /**
   * Обновить moderation.moderated_by
   * @param {Object} componentData - Данные компонента
   * @param {string} moderatorAddress - Адрес модератора
   * @param {string} status - Статус модерации
   * @returns {Object} Обновленные данные компонента
   */
  updateModeration(componentData, moderatorAddress, status) {
    const updated = { ...componentData };
    
    if (!updated.moderation) {
      updated.moderation = {};
    }
    
    updated.moderation.moderated_by = moderatorAddress;
    updated.moderation.moderated_at = new Date().toISOString();
    updated.moderation.status = status;
    
    return updated;
  }

  /**
   * Обновить sharing.shared_by
   * @param {Object} componentData - Данные компонента
   * @param {string} sharerAddress - Адрес, который поделился
   * @returns {Object} Обновленные данные компонента
   */
  updateSharing(componentData, sharerAddress) {
    const updated = { ...componentData };
    
    if (!updated.sharing) {
      updated.sharing = {};
    }
    
    updated.sharing.shared_by = sharerAddress;
    if (!updated.sharing.shared_at) {
      updated.sharing.shared_at = new Date().toISOString();
    }
    
    return updated;
  }

  /**
   * Добавить контрибьютора
   * @param {Object} componentData - Данные компонента
   * @param {string} address - Адрес контрибьютора
   * @param {string} role - Роль контрибьютора
   * @returns {Object} Обновленные данные компонента
   */
  addContributor(componentData, address, role) {
    const updated = { ...componentData };
    
    if (!updated.contributors) {
      updated.contributors = [];
    }
    
    // Проверяем, нет ли уже такого контрибьютора
    if (!this.hasContributor(updated, address)) {
      updated.contributors.push({
        address: address,
        role: role || 'contributor',
        added_at: new Date().toISOString()
      });
    }
    
    return updated;
  }

  /**
   * Добавить запись в change_history
   * @param {Object} componentData - Данные компонента
   * @param {Object} entry - Запись истории
   * @param {string} entry.timestamp - Временная метка
   * @param {string} entry.address - Адрес, выполнивший действие
   * @param {string} entry.action - Тип действия
   * @param {Array<string>} entry.changes - Список изменений
   * @param {string} entry.transaction_hash - Хеш транзакции
   * @param {number} entry.block_number - Номер блока
   * @returns {Object} Обновленные данные компонента
   */
  addHistoryEntry(componentData, entry) {
    const updated = { ...componentData };
    
    // Инициализировать change_history если отсутствует
    if (!updated.change_history) {
      updated.change_history = [];
    }
    
    // Добавить новую запись
    updated.change_history = [
      ...updated.change_history,
      {
        timestamp: entry.timestamp || new Date().toISOString(),
        address: entry.address,
        action: entry.action,
        changes: entry.changes || [],
        transaction_hash: entry.transaction_hash || '0x0000000000000000000000000000000000000000000000000000000000000000',
        block_number: entry.block_number || 0
      }
    ];
    
    return updated;
  }

  /**
   * Очистить тестовые адреса из исходного JSON файла компонента
   * 
   * **Назначение**: Обновить исходный JSON файл компонента на диске, заменив тестовые адреса на реальные.
   * Это нужно делать ДО загрузки в Arweave, чтобы исходные файлы были чистыми.
   * 
   * **Важно**: Эта функция **изменяет файл на диске**!
   * 
   * @param {string} componentJsonPath - Путь к исходному JSON файлу компонента
   * @param {string} realAddress - Реальный адрес seller'а
   * @returns {Object} Обновленные данные компонента
   */
  cleanSourceJson(componentJsonPath, realAddress) {
    const fs = require('fs');
    const path = require('path');
    
    // 1. Читаем исходный JSON файл
    if (!fs.existsSync(componentJsonPath)) {
      throw new Error(`JSON файл не найден: ${componentJsonPath}`);
    }
    
    const componentData = JSON.parse(fs.readFileSync(componentJsonPath, 'utf8'));
    
    // 2. Обновляем tracking-поля через updateForCreation
    // Это заменит все тестовые адреса на реальные
    const cleanedData = this.updateForCreation(componentData, {
      actorAddress: realAddress,
      action: 'create',
      blockchain: null
    });
    
    // 3. Сохраняем обновленный JSON обратно в файл
    fs.writeFileSync(componentJsonPath, JSON.stringify(cleanedData, null, 2), 'utf8');
    
    console.log(`   ✅ Очищен исходный JSON от тестовых адресов: ${path.basename(componentJsonPath)}`);
    console.log(`      → created_by: ${cleanedData.created_by}`);
    console.log(`      → contributors: ${cleanedData.contributors.length} записей`);
    
    return cleanedData;
  }

  /**
   * Обновить поля трассировки при создании компонента
   * 
   * **ВАЖНО**: Эта функция очищает тестовые адреса из данных компонента и заменяет их на реальные.
   * 
   * @param {Object} componentData - Исходные данные компонента (может содержать тестовые адреса)
   * @param {Object} context - Контекст создания
   * @param {string} context.actorAddress - Адрес создателя (реальный адрес seller'а)
   * @param {string} context.action - Действие ('create' | 'upload_to_arweave' | 'register_in_contract')
   * @param {Object} context.blockchain - Blockchain данные (опционально)
   * @param {string} context.blockchain.transactionHash - Хеш транзакции
   * @param {number} context.blockchain.blockNumber - Номер блока
   * @returns {Object} Обновленные данные компонента (с реальными адресами)
   */
  updateForCreation(componentData, context) {
    const { actorAddress, action, blockchain } = context;
    const timestamp = new Date().toISOString();
    
    // 1. Обновить ownership (created_by, contributors)
    let updated = this.updateOwnership(componentData, actorAddress);
    
    // 2. Обновить validator (если тестовый)
    if (this.isTestAddress(updated.metadata?.validation?.validator)) {
      updated = this.updateValidator(updated, actorAddress);
    }
    
    // 3. Обновить sharing.shared_by (если тестовый)
    if (this.isTestAddress(updated.sharing?.shared_by)) {
      updated = this.updateSharing(updated, actorAddress);
    }
    
    // 4. Добавить запись в change_history
    updated = this.addHistoryEntry(updated, {
      timestamp,
      address: actorAddress,
      action: action || 'create',
      changes: ['initial_creation'],
      transaction_hash: blockchain?.transactionHash || '0x0000000000000000000000000000000000000000000000000000000000000000',
      block_number: blockchain?.blockNumber || 0
    });
    
    // 5. Обновить last_updated
    updated.last_updated = timestamp;
    
    return updated;
  }

  /**
   * Обновить поля трассировки при модификации компонента
   * @param {Object} componentData - Текущие данные компонента
   * @param {Object} context - Контекст обновления
   * @param {string} context.actorAddress - Адрес, выполняющий обновление
   * @param {string} context.action - Действие ('update' | 'validate' | 'moderate' | 'share')
   * @param {Object} context.blockchain - Blockchain данные (опционально)
   * @param {Array<string>} context.changes - Список изменений
   * @param {string} context.status - Статус (для модерации)
   * @returns {Object} Обновленные данные компонента
   */
  updateForModification(componentData, context) {
    const { actorAddress, action, blockchain } = context;
    const timestamp = new Date().toISOString();
    
    let updated = { ...componentData };
    
    // В зависимости от типа действия
    switch (action) {
      case 'validate':
        updated = this.updateValidator(updated, actorAddress);
        if (!updated.metadata) {
          updated.metadata = {};
        }
        if (!updated.metadata.validation) {
          updated.metadata.validation = {};
        }
        updated.metadata.validation.last_validated = timestamp;
        break;
        
      case 'moderate':
        updated = this.updateModeration(updated, actorAddress, context.status || 'approved');
        break;
        
      case 'share':
        updated = this.updateSharing(updated, actorAddress);
        break;
        
      case 'update':
        // Обновление контента - добавляем в contributors если новый адрес
        if (!this.hasContributor(updated, actorAddress)) {
          updated = this.addContributor(updated, actorAddress, 'editor');
        }
        break;
    }
    
    // Добавить запись в change_history
    updated = this.addHistoryEntry(updated, {
      timestamp,
      address: actorAddress,
      action: action,
      changes: context.changes || [action],
      transaction_hash: blockchain?.transactionHash || '0x0000000000000000000000000000000000000000000000000000000000000000',
      block_number: blockchain?.blockNumber || 0
    });
    
    updated.last_updated = timestamp;
    
    return updated;
  }
}

module.exports = ComponentTracking;
