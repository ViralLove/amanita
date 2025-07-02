create table orders (
    id uuid primary key default gen_random_uuid(),
    order_hash bytea not null unique,
    buyer_address varchar not null,
    seller_address varchar not null,
    cart jsonb not null, -- массив из товаров и qty
    shipping_method_id uuid references shipping_methods(id),
    shipping_country_code varchar(2),
    shipping_cost float not null,
    subtotal float not null,
    otp integer not null,
    otp_amount float not null, -- сумма с OTP для вшивания в decimal
    status varchar default 'created',
    created_at timestamptz default now(),
    paid_at timestamptz
);

create table shipping_methods (
    id uuid primary key default gen_random_uuid(),
    seller_address varchar not null,
    name text not null,
    description text,
    cost float not null,
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
    created_at timestamptz default now()
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
    categories text[] not null,
    forms text[] not null,
    species text not null,
    updated_at timestamptz default now()
);

create table product_prices (
    id serial primary key,
    product_id text references products(id) on delete cascade,
    price numeric(18, 8) not null,
    currency text not null,
    weight numeric,
    weight_unit text,
    volume numeric,
    volume_unit text,
    form text
);


create table users (
    id uuid primary key default gen_random_uuid(),
    address varchar not null unique,
    joined_at timestamptz default now()
);

create table webhook_events (
    id serial primary key,
    source varchar, -- 'blockchain' / 'circle'
    event_type varchar,
    order_hash bytea,
    amount float,
    sender_address varchar,
    received_at timestamptz default now()
);
