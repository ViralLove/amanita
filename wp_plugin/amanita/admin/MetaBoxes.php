<?php
declare(strict_types=1);

namespace Amanita\Admin;

/**
 * MetaBoxes - метабоксы для интеграции с Amanita
 * 
 * @package Amanita
 */

if (!defined('ABSPATH')) {
    exit;
}

class MetaBoxes {
    
    public function __construct() {
        add_action('add_meta_boxes', array($this, 'add_sync_metabox'));
        add_action('admin_notices', array($this, 'show_sync_notices'));
    }
    
    /**
     * Добавляет метабокс синхронизации на страницу продукта
     */
    public function add_sync_metabox() {
        add_meta_box(
            'amanita-sync-metabox',
            __('Amanita Blockchain Sync', 'amanita'),
            array($this, 'render_sync_metabox'),
            'product',
            'side',
            'high'
        );
    }
    
    /**
     * Рендерит содержимое метабокса синхронизации
     */
    public function render_sync_metabox($post) {
        $product_id = $post->ID;
        $product = wc_get_product($product_id);
        
        if (!$product) {
            echo '<p>' . esc_html__('Product not found.', 'amanita') . '</p>';
            return;
        }
        
        // Получаем статус синхронизации
        $sync_status = get_post_meta($product_id, '_amanita_sync_status', true);
        $last_sync = get_post_meta($product_id, '_amanita_last_sync', true);
        $error_message = get_post_meta($product_id, '_amanita_sync_error', true);
        $blockchain_id = get_post_meta($product_id, '_amanita_blockchain_id', true);
        $ipfs_cid = get_post_meta($product_id, '_amanita_ipfs_cid', true);
        $tx_hash = get_post_meta($product_id, '_amanita_tx_hash', true);
        $is_active = get_post_meta($product_id, '_amanita_is_active', true);
        
        // Получаем последние логи
        $recent_logs = \Amanita\Logger::get_product_logs($product_id, 5);
        
        ?>
        <div class="amanita-metabox">
            
            <!-- Статус синхронизации -->
            <div class="amanita-status-section">
                <h4><?php echo esc_html__('Sync Status', 'amanita'); ?></h4>
                <div class="amanita-status-grid">
                    <div class="amanita-status-item <?php echo $sync_status === 'success' ? 'success' : ($sync_status === 'error' ? 'error' : 'warning'); ?>">
                        <div class="amanita-status-label"><?php echo esc_html__('Status', 'amanita'); ?></div>
                        <div class="amanita-status-value">
                            <?php 
                            switch ($sync_status) {
                                case 'success':
                                    echo '<span class="status-success">' . esc_html__('Synced', 'amanita') . '</span>';
                                    break;
                                case 'error':
                                    echo '<span class="status-error">' . esc_html__('Error', 'amanita') . '</span>';
                                    break;
                                case 'pending':
                                    echo '<span class="status-loading">' . esc_html__('Pending', 'amanita') . '</span>';
                                    break;
                                default:
                                    echo '<span class="status-loading">' . esc_html__('Not Synced', 'amanita') . '</span>';
                            }
                            ?>
                        </div>
                    </div>
            
            <?php if ($last_sync): ?>
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('Last Sync', 'amanita'); ?></div>
                        <div class="amanita-status-value">
                            <?php echo esc_html(date_i18n(get_option('date_format') . ' ' . get_option('time_format'), strtotime($last_sync))); ?>
                        </div>
                    </div>
                    <?php endif; ?>
                </div>
                
                <?php if ($error_message): ?>
                <div class="amanita-status-item error">
                    <div class="amanita-status-label"><?php echo esc_html__('Error', 'amanita'); ?></div>
                    <div class="amanita-status-value"><?php echo esc_html($error_message); ?></div>
                </div>
            <?php endif; ?>
            </div>
            
            <!-- Блокчейн информация -->
            <?php if ($blockchain_id || $ipfs_cid || $tx_hash): ?>
            <div class="amanita-blockchain-section">
                <h4><?php echo esc_html__('Blockchain Info', 'amanita'); ?></h4>
                <div class="amanita-status-grid">
                    <?php if ($blockchain_id): ?>
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('Blockchain ID', 'amanita'); ?></div>
                        <div class="amanita-status-value"><?php echo esc_html($blockchain_id); ?></div>
                    </div>
                    <?php endif; ?>
                    
                    <?php if ($ipfs_cid): ?>
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('IPFS CID', 'amanita'); ?></div>
                        <div class="amanita-status-value">
                            <a href="https://ipfs.io/ipfs/<?php echo esc_attr($ipfs_cid); ?>" target="_blank" title="<?php echo esc_attr__('View on IPFS', 'amanita'); ?>">
                                <?php echo esc_html(substr($ipfs_cid, 0, 20) . '...'); ?>
                            </a>
                        </div>
                    </div>
                    <?php endif; ?>
                    
                    <?php if ($tx_hash): ?>
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('Transaction Hash', 'amanita'); ?></div>
                        <div class="amanita-status-value">
                            <a href="https://etherscan.io/tx/<?php echo esc_attr($tx_hash); ?>" target="_blank" title="<?php echo esc_attr__('View on Etherscan', 'amanita'); ?>">
                                <?php echo esc_html(substr($tx_hash, 0, 20) . '...'); ?>
                            </a>
                        </div>
                    </div>
                    <?php endif; ?>
                    
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('Active Status', 'amanita'); ?></div>
                        <div class="amanita-status-value">
                            <?php echo $is_active ? '<span class="status-success">' . esc_html__('Active', 'amanita') . '</span>' : '<span class="status-error">' . esc_html__('Inactive', 'amanita') . '</span>'; ?>
                        </div>
                    </div>
                </div>
            </div>
            <?php endif; ?>
            
            <!-- Кнопки управления -->
            <div class="amanita-actions-section">
                <h4><?php echo esc_html__('Actions', 'amanita'); ?></h4>
                
                <div class="amanita-button-group">
                    <button type="button" 
                            class="amanita-button amanita-sync-product" 
                            data-product-id="<?php echo esc_attr($product_id); ?>"
                            <?php echo $sync_status === 'pending' ? 'disabled' : ''; ?>>
                        <?php echo esc_html__('Sync to Blockchain', 'amanita'); ?>
                    </button>
                    
                    <button type="button" 
                            class="amanita-button secondary amanita-refresh-status" 
                            data-product-id="<?php echo esc_attr($product_id); ?>">
                        <?php echo esc_html__('Refresh Status', 'amanita'); ?>
                    </button>
                </div>
                
                <?php if ($blockchain_id): ?>
                <div class="amanita-button-group">
                    <a href="https://etherscan.io/address/<?php echo esc_attr($blockchain_id); ?>" 
                       target="_blank" 
                       class="amanita-button secondary">
                        <?php echo esc_html__('View on Blockchain', 'amanita'); ?>
                    </a>
                </div>
                <?php endif; ?>
            </div>
            
            <!-- Последние логи -->
            <?php if (!empty($recent_logs)): ?>
            <div class="amanita-logs-section">
                <h4><?php echo esc_html__('Recent Activity', 'amanita'); ?></h4>
                <div class="amanita-logs">
                    <?php foreach (array_reverse($recent_logs) as $log): ?>
                    <div class="amanita-log-entry <?php echo strtolower($log['level']); ?>">
                        <div class="amanita-log-timestamp">
                            <?php echo esc_html(date_i18n('M j, Y H:i:s', $log['timestamp'])); ?>
                        </div>
                        <div class="amanita-log-level"><?php echo esc_html($log['level']); ?></div>
                        <div class="amanita-log-message"><?php echo esc_html($log['message']); ?></div>
                    </div>
                    <?php endforeach; ?>
                </div>
                <p class="description">
                    <a href="<?php echo esc_url(admin_url('admin.php?page=amanita-settings&tab=logs&product_id=' . $product_id)); ?>">
                        <?php echo esc_html__('View all logs', 'amanita'); ?>
                    </a>
                </p>
            </div>
            <?php endif; ?>
            
            <!-- Информация о продукте -->
            <div class="amanita-product-info">
                <h4><?php echo esc_html__('Product Info', 'amanita'); ?></h4>
                <div class="amanita-status-grid">
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('SKU', 'amanita'); ?></div>
                        <div class="amanita-status-value"><?php echo esc_html($product->get_sku() ?: __('N/A', 'amanita')); ?></div>
                    </div>
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('Price', 'amanita'); ?></div>
                        <div class="amanita-status-value"><?php echo esc_html($product->get_price_html()); ?></div>
                    </div>
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('Stock', 'amanita'); ?></div>
                        <div class="amanita-status-value">
                            <?php 
                            if ($product->is_in_stock()) {
                                echo '<span class="status-success">' . esc_html__('In Stock', 'amanita') . '</span>';
                            } else {
                                echo '<span class="status-error">' . esc_html__('Out of Stock', 'amanita') . '</span>';
                            }
                            ?>
                        </div>
                    </div>
                    <div class="amanita-status-item">
                        <div class="amanita-status-label"><?php echo esc_html__('Type', 'amanita'); ?></div>
                        <div class="amanita-status-value"><?php echo esc_html(ucfirst($product->get_type())); ?></div>
                    </div>
                </div>
            </div>
            
        </div>
        
        <style>
            .amanita-button-group {
                margin-bottom: 10px;
            }
            
            .amanita-button-group .amanita-button {
                margin-bottom: 5px;
            }
            
            .amanita-logs-section {
                margin-top: 20px;
            }
            
            .amanita-product-info {
                margin-top: 20px;
                padding-top: 15px;
                border-top: 1px solid #eee;
            }
        </style>
        <?php
    }
    
    /**
     * Показывает уведомления о синхронизации
     */
    public function show_sync_notices() {
        global $pagenow;
        
        // Показываем только на страницах продуктов
        if ($pagenow !== 'post.php' && $pagenow !== 'post-new.php') {
            return;
        }
        
        $post_type = get_post_type();
        if ($post_type !== 'product') {
            return;
        }
        
        // Проверяем параметры URL для уведомлений
        if (isset($_GET['amanita_sync_result'])) {
        $result = sanitize_text_field($_GET['amanita_sync_result']);
            $message = isset($_GET['amanita_sync_message']) ? urldecode($_GET['amanita_sync_message']) : '';
        
            $notice_class = $result === 'success' ? 'notice-success' : 'notice-error';
            $notice_message = '';
            
            switch ($result) {
                case 'success':
                    $notice_message = __('Product synchronized successfully with Amanita blockchain!', 'amanita');
                    break;
                case 'error':
                    $notice_message = $message ?: __('Failed to synchronize product with Amanita blockchain.', 'amanita');
                    break;
                case 'pending':
                    $notice_message = __('Product synchronization is in progress...', 'amanita');
                    $notice_class = 'notice-warning';
                    break;
            }
            
            if ($notice_message) {
                echo '<div class="notice ' . esc_attr($notice_class) . ' is-dismissible">';
                echo '<p>' . esc_html($notice_message) . '</p>';
                echo '</div>';
            }
        }
    }
}
