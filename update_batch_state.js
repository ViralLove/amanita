const fs = require('fs');
const path = require('path');

const batchStateFile = path.join(__dirname, 'scripts', 'organic_components', '_batch_state_localhost.json');

console.log('🔄 Обновление batch state...\n');

const batchState = JSON.parse(fs.readFileSync(batchStateFile, 'utf8'));

console.log('📊 Текущее состояние:');
console.log(`   → Completed: ${batchState.queue.completed.length}`);
console.log(`   → Failed: ${batchState.queue.failed.length}`);
console.log(`   → Pending: ${batchState.queue.pending.length}\n`);

// Все 11 компонентов
const allComponents = [
    'amanita_muscaria',
    'amanita_pantherina',
    'blue_lotus',
    'cantharellus_cibarius',
    'cordyceps_militaris',
    'inonotus_obliquus',
    'lions_mane',
    'mint',
    'nettle',
    'passionflower',
    'populus_tremula'
];

// Обновляем очереди
batchState.queue.completed = allComponents;
batchState.queue.failed = [];
batchState.queue.pending = [];

console.log('✅ Новое состояние:');
console.log(`   → Completed: ${batchState.queue.completed.length}`);
console.log(`   → Failed: ${batchState.queue.failed.length}`);
console.log(`   → Pending: ${batchState.queue.pending.length}\n`);

// Сохраняем с BigInt replacer
const replacer = (key, value) => 
    typeof value === 'bigint' ? value.toString() : value;
fs.writeFileSync(batchStateFile, JSON.stringify(batchState, replacer, 2), 'utf8');

console.log('✅ Batch state обновлен!');
