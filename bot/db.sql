create table orders (
    id uuid primary key default gen_random_uuid(),
    order_hash varchar(66) not null unique, -- ИЗМЕНЕНО: bytea -> varchar(66) для формата 0x...
    buyer_address varchar not null,
    seller_address varchar not null default current_setting('app.seller_address', true)::varchar, -- адрес продавца ноды
    cart jsonb not null, -- массив из товаров и qty
    shipping_method_id uuid references shipping_methods(id),
    shipping_country_code varchar(2),
    shipping_cost numeric(12,2) not null, -- ИЗМЕНЕНО: float -> numeric(12,2) для фиатных валют
    subtotal numeric(18,8) not null, -- ИЗМЕНЕНО: float -> numeric(18,8) для криптовалют
    otp integer not null,
    otp_amount numeric(18,8) not null, -- ИЗМЕНЕНО: float -> numeric(18,8) для криптовалют с OTP
    status varchar default 'created',
    created_at timestamptz default now(),
    paid_at timestamptz
);

create table shipping_methods (
    id uuid primary key default gen_random_uuid(),
    seller_address varchar not null default current_setting('app.seller_address', true)::varchar, -- адрес продавца ноды
    name text not null,
    description text,
    cost numeric(12,2) not null, -- ИЗМЕНЕНО: float -> numeric(12,2) для фиатных валют
    countries text[], -- ISO-коды стран, например ['US', 'CA', 'DE']
    created_at timestamptz default now()
);

create table product_descriptions (
    id TEXT PRIMARY KEY, -- CID
    title TEXT NOT NULL,
    scientific_name TEXT NOT NULL,
    generic_description TEXT NOT NULL,
    effects TEXT,
    shamanic TEXT,
    warnings TEXT,
    created_at timestamptz default now(),
    -- ИЗМЕНЕНО: добавлены поля для версионирования
    version integer not null default 1,
    created_by uuid references wallet_users(id)
);

create table dosage_instructions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description_id TEXT REFERENCES product_descriptions(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    title TEXT,
    description TEXT
);

CREATE TABLE product_categories (
    product_id TEXT REFERENCES products(id) ON DELETE CASCADE,
    category TEXT,
    PRIMARY KEY (product_id, category)
);

CREATE TABLE product_forms (
    product_id TEXT REFERENCES products(id) ON DELETE CASCADE,
    form TEXT,
    PRIMARY KEY (product_id, form)
);

create table products (
    id text primary key,
    alias text,
    status smallint default 1,
    cid text not null,
    title text not null,
    description_cid TEXT REFERENCES product_descriptions(id),
    cover_image_url text not null,
    species text not null,
    updated_at timestamptz default now()
);

create table product_prices (
    id serial primary key,
    product_id text references products(id) on delete cascade,
    price numeric(18, 8) not null,
    currency text not null,
    weight numeric,
    weight_unit text not null default 'g', -- ИЗМЕНЕНО: добавлены NOT NULL и DEFAULT
    volume numeric,
    volume_unit text not null default 'ml', -- ИЗМЕНЕНО: добавлены NOT NULL и DEFAULT
    form text
);

create table wallet_users (
    id uuid primary key default gen_random_uuid(),
    address varchar not null unique,
    joined_at timestamptz default now(),
    -- ИЗМЕНЕНО: добавлены поля для аудита и интеграции
    ip_address inet,
    telegram_user_id bigint,
    last_login timestamptz default now()
);

create table webhook_events (
    id serial primary key,
    source varchar, -- 'blockchain' / 'circle'
    event_type varchar,
    order_hash varchar(66), -- ИЗМЕНЕНО: bytea -> varchar(66) для формата 0x...
    amount numeric(18,8), -- ИЗМЕНЕНО: float -> numeric(18,8) для криптовалют из блокчейна
    sender_address varchar,
    received_at timestamptz default now()
);

-- ============================================================================
-- НЕДОСТАЮЩИЕ ТАБЛИЦЫ (АДАПТИРОВАНЫ ПОД ОДНУ НОДУ)
-- ============================================================================

-- История изменений статусов заказов для аудита
create table order_status_history (
    id uuid primary key default gen_random_uuid(),
    order_id uuid references orders(id) on delete cascade,
    old_status varchar,
    new_status varchar not null,
    changed_by varchar not null, -- адрес пользователя, изменившего статус
    reason text, -- причина изменения статуса
    created_at timestamptz default now()
);

-- Элементы корзины для сессий пользователей
create table cart_items (
    id uuid primary key default gen_random_uuid(),
    user_address varchar not null,
    product_id text references products(id) on delete cascade,
    quantity integer not null default 1,
    added_at timestamptz default now(),
    unique(user_address, product_id) -- один продукт в корзине пользователя
);

-- Транзакции платежей для детального отслеживания
create table payment_transactions (
    id uuid primary key default gen_random_uuid(),
    order_id uuid references orders(id) on delete cascade,
    tx_hash varchar not null unique, -- хэш транзакции в блокчейне
    amount numeric(18,8) not null, -- ИЗМЕНЕНО: float -> numeric(18,8) для криптовалют
    currency varchar(3) not null default 'ETH',
    sender_address varchar not null,
    receiver_address varchar not null default current_setting('app.seller_address', true)::varchar, -- адрес продавца ноды
    status varchar not null default 'pending' check (status in ('pending', 'confirmed', 'failed')), -- ИЗМЕНЕНО: добавлен check constraint
    confirmed_at timestamptz,
    created_at timestamptz default now()
);

-- Профиль продавца ноды (единственный для данной ноды)
create table seller_profile (
    id uuid primary key default gen_random_uuid(),
    seller_address varchar not null unique default current_setting('app.seller_address', true)::varchar, -- адрес продавца ноды
    display_name text,
    description text,
    logo_url text,
    website_url text,
    contact_email text,
    is_verified boolean default false,
    verification_date timestamptz,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

-- ============================================================================
-- ИНДЕКСЫ ДЛЯ ОПТИМИЗАЦИИ (АДАПТИРОВАНЫ ПОД ОДНУ НОДУ)
-- ============================================================================

-- Индексы для таблицы orders (все заказы принадлежат одному продавцу)
create index idx_orders_buyer_address on orders(buyer_address);
create index idx_orders_status on orders(status);
create index idx_orders_otp_amount on orders(otp_amount);
create index idx_orders_created_at on orders(created_at);
-- ИЗМЕНЕНО: добавлен уникальный индекс на orders.id (UUID должен быть уникальным)
create unique index idx_orders_id_unique on orders(id);

-- Индексы для таблицы products
create index idx_products_status on products(status);
-- ИЗМЕНЕНО: убраны GIN индексы на массивах, используются связи many-to-many
create index idx_products_species on products(species);
-- ИЗМЕНЕНО: добавлен уникальный индекс на products.id (CID должен быть уникальным)
create unique index idx_products_id_unique on products(id);

-- Индексы для таблиц связей many-to-many
create index idx_product_categories_product_id on product_categories(product_id);
create index idx_product_categories_category on product_categories(category);
create index idx_product_forms_product_id on product_forms(product_id);
create index idx_product_forms_form on product_forms(form);

-- Индексы для таблицы product_prices
create index idx_product_prices_product_id on product_prices(product_id);
create index idx_product_prices_currency on product_prices(currency);

-- Индексы для таблицы wallet_users
create index idx_wallet_users_address on wallet_users(address);
-- ИЗМЕНЕНО: добавлены индексы для новых полей аудита
create index idx_wallet_users_telegram_id on wallet_users(telegram_user_id);
create index idx_wallet_users_ip_address on wallet_users(ip_address);
create index idx_wallet_users_last_login on wallet_users(last_login);
-- ИЗМЕНЕНО: добавлен уникальный индекс на product_descriptions.id (CID должен быть уникальным)
create unique index idx_product_descriptions_id_unique on product_descriptions(id);
-- ИЗМЕНЕНО: добавлены индексы для полей версионирования
create index idx_product_descriptions_version on product_descriptions(version);
create index idx_product_descriptions_created_by on product_descriptions(created_by);

-- Индексы для таблицы webhook_events
create index idx_webhook_events_source on webhook_events(source);
create index idx_webhook_events_order_hash on webhook_events(order_hash);
create index idx_webhook_events_received_at on webhook_events(received_at);

-- Индексы для новых таблиц
create index idx_order_status_history_order_id on order_status_history(order_id);
create index idx_order_status_history_created_at on order_status_history(created_at);
create index idx_cart_items_user_address on cart_items(user_address);
create index idx_payment_transactions_order_id on payment_transactions(order_id);
create index idx_payment_transactions_tx_hash on payment_transactions(tx_hash);
create index idx_payment_transactions_status on payment_transactions(status);
-- ИЗМЕНЕНО: добавлен уникальный индекс на shipping_methods.id (UUID должен быть уникальным)
create unique index idx_shipping_methods_id_unique on shipping_methods(id);
-- ИЗМЕНЕНО: добавлен уникальный индекс на seller_profile.seller_address (единственный продавец на ноду)
create unique index idx_seller_profile_address_unique on seller_profile(seller_address);

-- Индексы для системы локализации
create index idx_languages_code on languages(code);
create index idx_languages_active on languages(is_active);

create index idx_category_dictionary_code on category_dictionary(code);
create index idx_category_translations_category_id on category_translations(category_id);
create index idx_category_translations_language on category_translations(language_code);

create index idx_form_dictionary_code on form_dictionary(code);
create index idx_form_translations_form_id on form_translations(form_id);
create index idx_form_translations_language on form_translations(language_code);

create index idx_measurement_units_code on measurement_units(code);
create index idx_measurement_units_type on measurement_units(unit_type);
create index idx_measurement_unit_translations_unit_id on measurement_unit_translations(unit_id);
create index idx_measurement_unit_translations_language on measurement_unit_translations(language_code);

create index idx_order_statuses_code on order_statuses(code);
create index idx_order_status_translations_status_id on order_status_translations(status_id);
create index idx_order_status_translations_language on order_status_translations(language_code);

create index idx_payment_statuses_code on payment_statuses(code);
create index idx_payment_status_translations_status_id on payment_status_translations(status_id);
create index idx_payment_status_translations_language on payment_status_translations(language_code);

create index idx_currencies_code on currencies(code);
create index idx_currency_translations_currency_id on currency_translations(currency_id);
create index idx_currency_translations_language on currency_translations(language_code);

-- ============================================================================
-- СОСТАВНЫЕ ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- ============================================================================

-- Составные индексы для переводов (оптимизация запросов с фильтрацией по нескольким столбцам)
create index idx_category_translations_lookup on category_translations(category_id, language_code);
create index idx_form_translations_lookup on form_translations(form_id, language_code);
create index idx_measurement_unit_translations_lookup on measurement_unit_translations(unit_id, language_code);
create index idx_order_status_translations_lookup on order_status_translations(status_id, language_code);
create index idx_payment_status_translations_lookup on payment_status_translations(status_id, language_code);
create index idx_currency_translations_lookup on currency_translations(currency_id, language_code);

-- Составные индексы для связей many-to-many (оптимизация JOIN операций)
create index idx_product_categories_lookup on product_categories(product_id, category);
create index idx_product_forms_lookup on product_forms(product_id, form);

-- Комментарии к индексам производительности
comment on index idx_category_translations_lookup is 'Составной индекс для быстрого поиска переводов категорий по ID и языку';
comment on index idx_form_translations_lookup is 'Составной индекс для быстрого поиска переводов форм по ID и языку';
comment on index idx_measurement_unit_translations_lookup is 'Составной индекс для быстрого поиска переводов единиц измерения по ID и языку';
comment on index idx_order_status_translations_lookup is 'Составной индекс для быстрого поиска переводов статусов заказов по ID и языку';
comment on index idx_payment_status_translations_lookup is 'Составной индекс для быстрого поиска переводов статусов платежей по ID и языку';
comment on index idx_currency_translations_lookup is 'Составной индекс для быстрого поиска переводов валют по ID и языку';
comment on index idx_product_categories_lookup is 'Составной индекс для быстрого поиска категорий продуктов';
comment on index idx_product_forms_lookup is 'Составной индекс для быстрого поиска форм продуктов';

-- ============================================================================
-- СИСТЕМА ЛОКАЛИЗАЦИИ (ТАБЛИЦЫ ПЕРЕВОДОВ ДЛЯ СЛОВАРЕЙ)
-- ============================================================================

-- Таблица поддерживаемых языков
create table languages (
    code varchar(5) primary key, -- 'en', 'ru', 'es', 'fr', 'de', etc.
    name text not null, -- English, Русский, Español, Français, Deutsch
    native_name text not null, -- English, Русский, Español, Français, Deutsch
    is_active boolean default true,
    created_at timestamptz default now()
);

-- ============================================================================
-- БАЗОВЫЕ ДАННЫЕ: ЯЗЫКИ (ИЗ BOT/TEMPLATES)
-- ============================================================================

-- Вставка поддерживаемых языков из bot/templates
insert into languages (code, name, native_name) values ('ru', 'Russian', 'Русский');
insert into languages (code, name, native_name) values ('en', 'English', 'English');
insert into languages (code, name, native_name) values ('es', 'Spanish', 'Español');
insert into languages (code, name, native_name) values ('de', 'German', 'Deutsch');
insert into languages (code, name, native_name) values ('fr', 'French', 'Français');
insert into languages (code, name, native_name) values ('no', 'Norwegian', 'Norsk');
insert into languages (code, name, native_name) values ('da', 'Danish', 'Dansk');
insert into languages (code, name, native_name) values ('sv', 'Swedish', 'Svenska');
insert into languages (code, name, native_name) values ('fi', 'Finnish', 'Suomi');
insert into languages (code, name, native_name) values ('et', 'Estonian', 'Eesti');
insert into languages (code, name, native_name) values ('lv', 'Latvian', 'Latviešu');
insert into languages (code, name, native_name) values ('lt', 'Lithuanian', 'Lietuvių');
insert into languages (code, name, native_name) values ('pl', 'Polish', 'Polski');
insert into languages (code, name, native_name) values ('nl', 'Dutch', 'Nederlands');
insert into languages (code, name, native_name) values ('pt', 'Portuguese', 'Português');

-- Словарь категорий продуктов (для переводов)
create table category_dictionary (
    id uuid primary key default gen_random_uuid(),
    code varchar(50) unique not null, -- 'mushrooms', 'herbs', 'supplements', etc.
    created_at timestamptz default now()
);

-- Переводы категорий продуктов
create table category_translations (
    category_id uuid references category_dictionary(id) on delete cascade,
    language_code varchar(5) references languages(code),
    name text not null,
    description text,
    primary key (category_id, language_code)
);

-- Словарь форм продуктов (для переводов)
create table form_dictionary (
    id uuid primary key default gen_random_uuid(),
    code varchar(50) unique not null, -- 'powder', 'tincture', 'whole', 'capsules', etc.
    created_at timestamptz default now()
);

-- Переводы форм продуктов
create table form_translations (
    form_id uuid references form_dictionary(id) on delete cascade,
    language_code varchar(5) references languages(code),
    name text not null,
    description text,
    primary key (form_id, language_code)
);

-- Словарь единиц измерения
create table measurement_units (
    id uuid primary key default gen_random_uuid(),
    code varchar(20) unique not null, -- 'g', 'kg', 'ml', 'l', 'pieces', etc.
    unit_type text check (unit_type in ('weight', 'volume', 'length', 'count')) not null,
    created_at timestamptz default now()
);

-- Переводы единиц измерения
create table measurement_unit_translations (
    unit_id uuid references measurement_units(id) on delete cascade,
    language_code varchar(5) references languages(code),
    name text not null, -- грамм, килограмм, миллилитр, литр, штука
    short_name text not null, -- г, кг, мл, л, шт
    primary key (unit_id, language_code)
);

-- Словарь статусов заказов
create table order_statuses (
    id uuid primary key default gen_random_uuid(),
    code varchar(30) unique not null, -- 'pending', 'confirmed', 'shipped', 'delivered', 'cancelled'
    created_at timestamptz default now()
);

-- Переводы статусов заказов
create table order_status_translations (
    status_id uuid references order_statuses(id) on delete cascade,
    language_code varchar(5) references languages(code),
    name text not null,
    description text,
    primary key (status_id, language_code)
);

-- Словарь статусов платежей
create table payment_statuses (
    id uuid primary key default gen_random_uuid(),
    code varchar(30) unique not null, -- 'pending', 'confirmed', 'failed'
    created_at timestamptz default now()
);

-- Переводы статусов платежей
create table payment_status_translations (
    status_id uuid references payment_statuses(id) on delete cascade,
    language_code varchar(5) references languages(code),
    name text not null,
    description text,
    primary key (status_id, language_code)
);

-- Словарь валют
create table currencies (
    id uuid primary key default gen_random_uuid(),
    code varchar(3) unique not null, -- 'ETH', 'USD', 'EUR', 'RUB'
    symbol varchar(10) not null, -- 'Ξ', '$', '€', '₽'
    created_at timestamptz default now()
);

-- Переводы названий валют
create table currency_translations (
    currency_id uuid references currencies(id) on delete cascade,
    language_code varchar(5) references languages(code),
    name text not null, -- Ethereum, Доллар США, Евро, Рубль
    primary key (currency_id, language_code)
);

-- ============================================================================
-- RLS (ROW LEVEL SECURITY) ПОЛИТИКИ (АДАПТИРОВАНЫ ПОД ОДНУ НОДУ)
-- ============================================================================

-- Включаем RLS на таблицах с пользовательскими данными
alter table orders enable row level security;
alter table wallet_users enable row level security;
alter table cart_items enable row level security;
alter table order_status_history enable row level security;
-- ИЗМЕНЕНО: добавлен RLS на дополнительные таблицы с пользовательскими данными
alter table payment_transactions enable row level security;
alter table seller_profile enable row level security;
alter table webhook_events enable row level security;

-- Политика для orders: покупатели видят только свои заказы, продавец видит все заказы своей ноды
create policy "Buyers can view their own orders" on orders
    for select using (buyer_address = current_setting('app.current_user_address', true)::varchar);

create policy "Seller can view all orders" on orders
    for select using (seller_address = current_setting('app.seller_address', true)::varchar);

create policy "Buyers can create orders" on orders
    for insert with check (buyer_address = current_setting('app.current_user_address', true)::varchar);

create policy "Seller can update orders" on orders
    for update using (seller_address = current_setting('app.seller_address', true)::varchar);

-- Политика для wallet_users: пользователи видят только свои данные
create policy "Wallet users can view their own profile" on wallet_users
    for select using (address = current_setting('app.current_user_address', true)::varchar);

create policy "Wallet users can insert their profile" on wallet_users
    for insert with check (address = current_setting('app.current_user_address', true)::varchar);

create policy "Wallet users can update their profile" on wallet_users
    for update using (address = current_setting('app.current_user_address', true)::varchar);

-- Политика для cart_items: пользователи управляют своей корзиной
create policy "Users can manage their cart" on cart_items
    for all using (user_address = current_setting('app.current_user_address', true)::varchar);

-- Политика для order_status_history: доступ к истории заказов
create policy "Order history access" on order_status_history
    for select using (
        exists (
            select 1 from orders 
            where orders.id = order_status_history.order_id 
            and (orders.buyer_address = current_setting('app.current_user_address', true)::varchar
                 or orders.seller_address = current_setting('app.seller_address', true)::varchar)
        )
    );

-- Политика для payment_transactions: доступ к транзакциям платежей
create policy "Payment transactions access" on payment_transactions
    for select using (
        exists (
            select 1 from orders 
            where orders.id = payment_transactions.order_id 
            and (orders.buyer_address = current_setting('app.current_user_address', true)::varchar
                 or orders.seller_address = current_setting('app.seller_address', true)::varchar)
        )
    );

create policy "Payment transactions insert" on payment_transactions
    for insert with check (
        exists (
            select 1 from orders 
            where orders.id = payment_transactions.order_id 
            and (orders.buyer_address = current_setting('app.current_user_address', true)::varchar
                 or orders.seller_address = current_setting('app.seller_address', true)::varchar)
        )
    );

-- Политика для seller_profile: только продавец ноды может управлять своим профилем
create policy "Seller profile management" on seller_profile
    for all using (seller_address = current_setting('app.seller_address', true)::varchar);

-- Политика для webhook_events: доступ к событиям вебхуков
create policy "Webhook events access" on webhook_events
    for select using (
        exists (
            select 1 from orders 
            where orders.order_hash = webhook_events.order_hash 
            and (orders.buyer_address = current_setting('app.current_user_address', true)::varchar
                 or orders.seller_address = current_setting('app.seller_address', true)::varchar)
        )
    );

create policy "Webhook events insert" on webhook_events
    for insert with check (
        exists (
            select 1 from orders 
            where orders.order_hash = webhook_events.order_hash 
            and (orders.buyer_address = current_setting('app.current_user_address', true)::varchar
                 or orders.seller_address = current_setting('app.seller_address', true)::varchar)
        )
    );

-- Публичный доступ на чтение для продуктов и описаний (каталог)
-- RLS не включаем для products, product_descriptions, product_prices - публичный доступ

-- Комментарии к RLS политикам
comment on policy "Buyers can view their own orders" on orders is 'Покупатели видят только свои заказы';
comment on policy "Seller can view all orders" on orders is 'Продавец видит все заказы своей ноды';
comment on policy "Buyers can create orders" on orders is 'Покупатели могут создавать заказы';
comment on policy "Seller can update orders" on orders is 'Продавец может обновлять статусы заказов';

comment on policy "Wallet users can view their own profile" on wallet_users is 'Пользователи видят только свой профиль';
comment on policy "Wallet users can insert their profile" on wallet_users is 'Пользователи могут создавать свой профиль';
comment on policy "Wallet users can update their profile" on wallet_users is 'Пользователи могут обновлять свой профиль';

comment on policy "Users can manage their cart" on cart_items is 'Пользователи управляют только своей корзиной';

comment on policy "Order history access" on order_status_history is 'Доступ к истории заказов для участников';

comment on policy "Payment transactions access" on payment_transactions is 'Доступ к транзакциям платежей для участников заказа';
comment on policy "Payment transactions insert" on payment_transactions is 'Создание транзакций платежей для участников заказа';

comment on policy "Seller profile management" on seller_profile is 'Продавец управляет своим профилем';

comment on policy "Webhook events access" on webhook_events is 'Доступ к событиям вебхуков для участников заказа';
comment on policy "Webhook events insert" on webhook_events is 'Создание событий вебхуков для участников заказа';

-- ============================================================================
-- ПРЕДСТАВЛЕНИЯ (VIEWS) (АДАПТИРОВАНЫ ПОД ОДНУ НОДУ)
-- ============================================================================

-- Продукты с переводами категорий и форм
create view products_with_translations as
select 
    p.id,
    p.alias,
    p.status,
    p.cid,
    p.title,
    p.description_cid,
    p.cover_image_url,
    p.species,
    p.updated_at,
    -- ИЗМЕНЕНО: агрегация переводов категорий и форм
    array_agg(DISTINCT ct.name) as category_names,
    array_agg(DISTINCT ft.name) as form_names
from products p
left join product_categories pc on p.id = pc.product_id
left join category_dictionary cd on pc.category = cd.code
left join category_translations ct on cd.id = ct.category_id
left join product_forms pf on p.id = pf.product_id
left join form_dictionary fd on pf.form = fd.code
left join form_translations ft on fd.id = ft.form_id
group by p.id, p.alias, p.status, p.cid, p.title, p.description_cid, p.cover_image_url, p.species, p.updated_at;

-- Только активные продукты ноды с категориями и формами через связи many-to-many
create view view_active_products as
select 
    p.id,
    p.alias,
    p.cid,
    p.title,
    p.description_cid,
    p.cover_image_url,
    -- ИЗМЕНЕНО: категории и формы через агрегацию из связей many-to-many
    array_agg(DISTINCT pc.category) as categories,
    array_agg(DISTINCT pf.form) as forms,
    p.species,
    p.updated_at,
    pd.scientific_name,
    pd.generic_description,
    pd.effects,
    pd.shamanic,
    pd.warnings
from products p
left join product_descriptions pd on p.description_cid = pd.id
left join product_categories pc on p.id = pc.product_id
left join product_forms pf on p.id = pf.product_id
where p.status = 1
group by p.id, p.alias, p.cid, p.title, p.description_cid, p.cover_image_url, p.species, p.updated_at,
         pd.scientific_name, pd.generic_description, pd.effects, pd.shamanic, pd.warnings;

-- Сводка по заказам ноды
create view view_order_summary as
select 
    o.id,
    o.order_hash,
    o.buyer_address,
    o.seller_address,
    o.status,
    o.subtotal,
    o.shipping_cost,
    (o.subtotal + o.shipping_cost) as total_amount,
    o.otp,
    o.otp_amount,
    o.created_at,
    o.paid_at,
    sm.name as shipping_method_name,
    jsonb_array_length(o.cart) as items_count
from orders o
left join shipping_methods sm on o.shipping_method_id = sm.id
where o.seller_address = current_setting('app.seller_address', true)::varchar;

-- Заказы ноды с деталями покупателей
create view view_seller_orders as
select 
    o.id,
    o.order_hash,
    o.buyer_address,
    o.seller_address,
    o.cart,
    o.status,
    o.subtotal,
    o.shipping_cost,
    (o.subtotal + o.shipping_cost) as total_amount,
    o.otp_amount,
    o.created_at,
    o.paid_at,
    sm.name as shipping_method_name,
    sm.countries as shipping_countries,
    u.joined_at as buyer_joined_at
from orders o
left join shipping_methods sm on o.shipping_method_id = sm.id
left join wallet_users u on o.buyer_address = u.address
where o.seller_address = current_setting('app.seller_address', true)::varchar;

-- Способы доставки ноды
create view view_shipping_methods as
select 
    id,
    name,
    description,
    cost,
    countries,
    created_at
from shipping_methods
where seller_address = current_setting('app.seller_address', true)::varchar;

-- ============================================================================
-- ТРИГГЕРЫ
-- ============================================================================

-- Функция для обновления updated_at в таблице products
create or replace function update_products_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Триггер для автоматического обновления updated_at
create trigger trigger_products_updated_at
    before update on products
    for each row
    execute function update_products_updated_at();

-- Функция для логирования изменений статусов заказов
create or replace function log_order_status_change()
returns trigger as $$
begin
    if old.status is distinct from new.status then
        insert into order_status_history (
            order_id,
            old_status,
            new_status,
            changed_by,
            reason
        ) values (
            new.id,
            old.status,
            new.status,
            current_setting('app.current_user_address', true)::varchar,
            'Status updated'
        );
    end if;
    return new;
end;
$$ language plpgsql;

-- Триггер для логирования изменений статусов
create trigger trigger_order_status_change
    after update on orders
    for each row
    execute function log_order_status_change();

-- Функция для обновления updated_at в seller_profile
create or replace function update_seller_profile_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Триггер для автоматического обновления updated_at в seller_profile
create trigger trigger_seller_profile_updated_at
    before update on seller_profile
    for each row
    execute function update_seller_profile_updated_at();

-- ============================================================================
-- БАЗОВЫЕ ДАННЫЕ: СЛОВАРИ (ИЗ ACTIVE_CATALOG.JSON)
-- ============================================================================

-- Вставка категорий продуктов из каталога
insert into category_dictionary (code) values ('mushroom');
insert into category_dictionary (code) values ('plant');
insert into category_dictionary (code) values ('mental health');
insert into category_dictionary (code) values ('focus');
insert into category_dictionary (code) values ('ADHD support');
insert into category_dictionary (code) values ('mental force');
insert into category_dictionary (code) values ('immune system');
insert into category_dictionary (code) values ('vital force');
insert into category_dictionary (code) values ('antiparasite');

-- Вставка форм продуктов из каталога
insert into form_dictionary (code) values ('mixed slices');
insert into form_dictionary (code) values ('whole caps');
insert into form_dictionary (code) values ('broken caps');
insert into form_dictionary (code) values ('premium caps');
insert into form_dictionary (code) values ('unknown');
insert into form_dictionary (code) values ('powder');
insert into form_dictionary (code) values ('tincture');
insert into form_dictionary (code) values ('flower');
insert into form_dictionary (code) values ('chunks');
insert into form_dictionary (code) values ('dried whole');
insert into form_dictionary (code) values ('dried powder');
insert into form_dictionary (code) values ('dried strips');
insert into form_dictionary (code) values ('whole dried');

-- Вставка единиц измерения из каталога
insert into measurement_units (code, unit_type) values ('g', 'weight');
insert into measurement_units (code, unit_type) values ('ml', 'volume');

-- Вставка валют из каталога
insert into currencies (code, symbol) values ('EUR', '€');

-- Вставка статусов заказов (стандартные)
insert into order_statuses (code) values ('pending');
insert into order_statuses (code) values ('confirmed');
insert into order_statuses (code) values ('shipped');
insert into order_statuses (code) values ('delivered');
insert into order_statuses (code) values ('cancelled');

-- Вставка статусов платежей (стандартные)
insert into payment_statuses (code) values ('pending');
insert into payment_statuses (code) values ('confirmed');
insert into payment_statuses (code) values ('failed');

-- ============================================================================
-- ПРИМЕЧАНИЕ: ПЕРЕВОДЫ СЛОВАРЕЙ
-- ============================================================================
-- Переводы для всех языков находятся в отдельном файле: bot/db_dict_data.md
-- Для добавления переводов выполните соответствующие INSERT запросы из этого файла

-- ============================================================================
-- КОММЕНТАРИИ И ДОКУМЕНТАЦИЯ (АДАПТИРОВАНЫ ПОД ОДНУ НОДУ)
-- ============================================================================

comment on table orders is 'Заказы пользователей ноды с OTP системой для платежей';
comment on table shipping_methods is 'Способы доставки ноды';
comment on table products is 'Кэш продуктов ноды из блокчейна (без массивов, используются связи many-to-many)';
comment on table product_categories is 'Связи продуктов с категориями (many-to-many)';
comment on table product_forms is 'Связи продуктов с формами (many-to-many)';
comment on table product_descriptions is 'Детальные описания продуктов (IPFS CID)';
comment on table product_prices is 'Цены продуктов с поддержкой веса/объема';
comment on table wallet_users is 'Пользователи кошельков ноды (переименовано из users для избежания конфликтов)';
comment on table webhook_events is 'События для интеграций с блокчейном';
comment on table order_status_history is 'История изменений статусов заказов ноды';
comment on table cart_items is 'Элементы корзины для сессий пользователей ноды';
comment on table payment_transactions is 'Транзакции платежей ноды для отслеживания';
comment on table seller_profile is 'Профиль продавца ноды';

-- Комментарии для новых полей аудита
comment on column wallet_users.ip_address is 'IP адрес пользователя для аудита безопасности';
comment on column wallet_users.telegram_user_id is 'Telegram ID пользователя для интеграции с ботом';
comment on column wallet_users.last_login is 'Время последнего входа пользователя';
comment on column product_descriptions.version is 'Версия описания продукта';
comment on column product_descriptions.created_by is 'Пользователь, создавший описание';

-- Комментарии для представлений
comment on view products_with_translations is 'Продукты с переведенными названиями категорий и форм для мультиязычного интерфейса';

-- Комментарии для системы локализации
comment on table languages is 'Поддерживаемые языки системы';
comment on table category_dictionary is 'Словарь категорий продуктов (мультиязычный)';
comment on table category_translations is 'Переводы названий категорий продуктов';
comment on table form_dictionary is 'Словарь форм продуктов (мультиязычный)';
comment on table form_translations is 'Переводы названий форм продуктов';
comment on table measurement_units is 'Словарь единиц измерения (мультиязычный)';
comment on table measurement_unit_translations is 'Переводы единиц измерения';
comment on table order_statuses is 'Словарь статусов заказов (мультиязычный)';
comment on table order_status_translations is 'Переводы статусов заказов';
comment on table payment_statuses is 'Словарь статусов платежей (мультиязычный)';
comment on table payment_status_translations is 'Переводы статусов платежей';
comment on table currencies is 'Словарь валют (мультиязычный)';
comment on table currency_translations is 'Переводы названий валют';

comment on column orders.otp is 'OTP код для верификации платежа';
comment on column orders.otp_amount is 'Сумма с встроенным OTP для платежа (numeric(18,8) для точности)';
comment on column orders.shipping_cost is 'Стоимость доставки (numeric(12,2) для фиатных валют)';
comment on column orders.subtotal is 'Подытог заказа (numeric(18,8) для криптовалют)';
comment on column orders.order_hash is 'Хэш транзакции в блокчейне (varchar(66) для формата 0x...)';
comment on column product_prices.weight_unit is 'Единица измерения веса (по умолчанию g)';
comment on column product_prices.volume_unit is 'Единица измерения объёма (по умолчанию ml)';
comment on column payment_transactions.status is 'Статус транзакции (pending/confirmed/failed)';
comment on column webhook_events.order_hash is 'Хэш транзакции в блокчейне (varchar(66) для формата 0x...)';
comment on column orders.seller_address is 'Адрес продавца ноды (автоматически устанавливается)';
comment on column products.cid is 'IPFS Content Identifier метаданных';
comment on column product_prices.price is 'Цена с точностью до 8 знаков после запятой';
comment on column shipping_methods.cost is 'Стоимость доставки (numeric(12,2) для фиатных валют)';
comment on column payment_transactions.amount is 'Сумма транзакции (numeric(18,8) для криптовалют)';
comment on column webhook_events.amount is 'Сумма события (numeric(18,8) для криптовалют)';
comment on column seller_profile.seller_address is 'Адрес продавца ноды (единственный для данной ноды)';
