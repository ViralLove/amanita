<?php
/**
 * Uninstaller - файл для автоматического удаления плагина WordPress
 * 
 * Этот файл должен находиться в корне плагина
 * WordPress автоматически вызывает его при удалении плагина
 * 
 * @package Amanita
 */

// Если файл вызван напрямую, прерываем выполнение
if (!defined('WP_UNINSTALL_PLUGIN')) {
    die;
}

// Загружаем основной класс Uninstaller
if (class_exists('\Amanita\Uninstaller')) {
    \Amanita\Uninstaller::cleanup();
} 