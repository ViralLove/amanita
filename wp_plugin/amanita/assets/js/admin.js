/**
 * Amanita Admin JavaScript
 * 
 * @package Amanita
 */

(function($) {
    'use strict';
    
    // Основной объект плагина
    var AmanitaAdmin = {
        
        /**
         * Инициализация
         */
        init: function() {
            this.bindEvents();
            this.checkConnectionStatus();
            this.loadStatistics();
        },
        
        /**
         * Привязка событий
         */
        bindEvents: function() {
            // Тестирование соединения
            $('#amanita-test-connection').on('click', this.testConnection);
            
            // Синхронизация продукта
            $('.amanita-sync-product').on('click', this.syncProduct);
            
            // Обновление статуса продукта
            $('.amanita-refresh-status').on('click', this.refreshProductStatus);
            
            // Автообновление статуса каждые 30 секунд
            setInterval(this.updateConnectionStatus, 30000);
        },
        
        /**
         * Проверка статуса соединения
         */
        checkConnectionStatus: function() {
            var $indicator = $('#amanita-status-indicator');
            
            $indicator.html('<span class="status-loading">' + amanita_ajax.strings.checking_connection + '</span>');
            
            $.ajax({
                url: amanita_ajax.ajax_url,
                type: 'POST',
                data: {
                    action: 'amanita_test_connection',
                    nonce: amanita_ajax.nonce
                },
                success: function(response) {
                    if (response.success) {
                        $indicator.html('<span class="status-success">' + amanita_ajax.strings.connection_success + '</span>');
                    } else {
                        $indicator.html('<span class="status-error">' + (response.message || amanita_ajax.strings.connection_error) + '</span>');
                    }
                },
                error: function() {
                    $indicator.html('<span class="status-error">' + amanita_ajax.strings.connection_error + '</span>');
                }
            });
        },
        
        /**
         * Тестирование соединения
         */
        testConnection: function(e) {
            e.preventDefault();
            
            var $button = $(this);
            var originalText = $button.text();
            
            $button.prop('disabled', true).text(amanita_ajax.strings.testing_connection);
            
            $.ajax({
                url: amanita_ajax.ajax_url,
                type: 'POST',
                data: {
                    action: 'amanita_test_connection',
                    nonce: amanita_ajax.nonce
                },
                success: function(response) {
                    if (response.success) {
                        AmanitaAdmin.showNotice(amanita_ajax.strings.connection_success, 'success');
                        $('#amanita-status-indicator').html('<span class="status-success">' + amanita_ajax.strings.connection_success + '</span>');
                    } else {
                        AmanitaAdmin.showNotice(response.message || amanita_ajax.strings.connection_error, 'error');
                        $('#amanita-status-indicator').html('<span class="status-error">' + (response.message || amanita_ajax.strings.connection_error) + '</span>');
                    }
                },
                error: function() {
                    AmanitaAdmin.showNotice(amanita_ajax.strings.connection_error, 'error');
                    $('#amanita-status-indicator').html('<span class="status-error">' + amanita_ajax.strings.connection_error + '</span>');
                },
                complete: function() {
                    $button.prop('disabled', false).text(originalText);
                }
            });
        },
        
        /**
         * Синхронизация продукта
         */
        syncProduct: function(e) {
            e.preventDefault();
            
            var $button = $(this);
            var productId = $button.data('product-id');
            var originalText = $button.text();
            
            $button.prop('disabled', true).text(amanita_ajax.strings.syncing);
            
            $.ajax({
                url: amanita_ajax.ajax_url,
                type: 'POST',
                data: {
                    action: 'amanita_sync_product',
                    product_id: productId,
                    nonce: amanita_ajax.nonce
                },
                success: function(response) {
                    if (response.success) {
                        AmanitaAdmin.showNotice(amanita_ajax.strings.sync_success, 'success');
                        AmanitaAdmin.updateProductStatus(productId, response);
                    } else {
                        AmanitaAdmin.showNotice(response.message || amanita_ajax.strings.sync_error, 'error');
                    }
                },
                error: function() {
                    AmanitaAdmin.showNotice(amanita_ajax.strings.sync_error, 'error');
                },
                complete: function() {
                    $button.prop('disabled', false).text(originalText);
                }
            });
        },
        
        /**
         * Обновление статуса продукта
         */
        refreshProductStatus: function(e) {
            e.preventDefault();
            
            var $button = $(this);
            var productId = $button.data('product-id');
            
            $.ajax({
                url: amanita_ajax.ajax_url,
                type: 'POST',
                data: {
                    action: 'amanita_get_product_status',
                    product_id: productId,
                    nonce: amanita_ajax.nonce
                },
                success: function(response) {
                    if (response.success) {
                        AmanitaAdmin.updateProductStatus(productId, response);
                    }
                }
            });
        },
        
        /**
         * Обновление статуса продукта в UI
         */
        updateProductStatus: function(productId, response) {
            var $statusContainer = $('.amanita-product-status[data-product-id="' + productId + '"]');
            
            if ($statusContainer.length) {
                var statusHtml = '';
                
                if (response.status) {
                    statusHtml += '<div class="status-item"><strong>Status:</strong> ' + response.status + '</div>';
                }
                
                if (response.last_sync) {
                    statusHtml += '<div class="status-item"><strong>Last Sync:</strong> ' + response.last_sync + '</div>';
                }
                
                if (response.error_message) {
                    statusHtml += '<div class="status-item error"><strong>Error:</strong> ' + response.error_message + '</div>';
                }
                
                $statusContainer.html(statusHtml);
            }
        },
        
        /**
         * Автообновление статуса соединения
         */
        updateConnectionStatus: function() {
            // Обновляем только если страница активна
            if (!document.hidden) {
                AmanitaAdmin.checkConnectionStatus();
            }
        },
        
        /**
         * Загрузка статистики
         */
        loadStatistics: function() {
            // Здесь можно добавить AJAX загрузку статистики
            // Пока используем заглушки
            $('#amanita-synced-products').text('0');
            $('#amanita-synced-orders').text('0');
            $('#amanita-sync-errors').text('0');
        },
        
        /**
         * Показ уведомлений
         */
        showNotice: function(message, type) {
            var noticeClass = type === 'success' ? 'notice-success' : 'notice-error';
            var noticeHtml = '<div class="notice ' + noticeClass + ' is-dismissible"><p>' + message + '</p></div>';
            
            // Удаляем старые уведомления
            $('.amanita-notice').remove();
            
            // Добавляем новое уведомление
            var $notice = $(noticeHtml).addClass('amanita-notice');
            $('.wrap h1').after($notice);
            
            // Автоматически скрываем через 5 секунд
            setTimeout(function() {
                $notice.fadeOut();
            }, 5000);
        },
        
        /**
         * Валидация формы настроек
         */
        validateSettings: function() {
            var isValid = true;
            var errors = [];
            
            // Проверка URL
            var url = $('input[name="amanita_python_service_url"]').val();
            if (url && !AmanitaAdmin.isValidUrl(url)) {
                errors.push('Please enter a valid URL for Python Service');
                isValid = false;
            }
            
            // Проверка wallet address
            var wallet = $('input[name="amanita_seller_wallet_address"]').val();
            if (wallet && !AmanitaAdmin.isValidWalletAddress(wallet)) {
                errors.push('Please enter a valid Ethereum wallet address');
                isValid = false;
            }
            
            // Показываем ошибки
            if (!isValid) {
                AmanitaAdmin.showNotice(errors.join('<br>'), 'error');
            }
            
            return isValid;
        },
        
        /**
         * Проверка валидности URL
         */
        isValidUrl: function(string) {
            try {
                new URL(string);
                return true;
            } catch (_) {
                return false;
            }
        },
        
        /**
         * Проверка валидности Ethereum адреса
         */
        isValidWalletAddress: function(address) {
            return /^0x[a-fA-F0-9]{40}$/.test(address);
        }
    };
    
    // Инициализация при загрузке документа
    $(document).ready(function() {
        AmanitaAdmin.init();
        
        // Валидация формы настроек
        $('form[action="options.php"]').on('submit', function(e) {
            if (!AmanitaAdmin.validateSettings()) {
                e.preventDefault();
            }
        });
    });
    
})(jQuery); 