-- ============================================================
-- 01_schema.sql
-- Esquema estrela do projeto Olist BI
-- ------------------------------------------------------------
-- Modelo dimensional no grao de item de pedido.
-- 1 tabela fato + 5 dimensoes.
-- As tabelas sao criadas pelo ETL em Python (to_sql), mas este
-- arquivo documenta a intencao do modelo: tipos, chaves primarias
-- e relacionamentos entre fato e dimensoes.
-- ============================================================

-- ---------- DIMENSOES ----------

-- Clientes. customer_id e a chave de pedido; customer_unique_id
-- identifica a pessoa real (usado para clientes recorrentes).
CREATE TABLE dim_customer (
    customer_id        TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    zip_prefix         INTEGER,
    city               TEXT,
    state              TEXT
);

-- Produtos, com categoria em portugues e ingles.
CREATE TABLE dim_product (
    product_id          TEXT PRIMARY KEY,
    category_pt         TEXT,
    category_en         TEXT,
    weight_g            REAL,
    product_length_cm   REAL,
    product_height_cm   REAL,
    product_width_cm    REAL
);

-- Vendedores do marketplace.
CREATE TABLE dim_seller (
    seller_id   TEXT PRIMARY KEY,
    zip_prefix  INTEGER,
    city        TEXT,
    state       TEXT
);

-- Pedido: atributos descritivos no nivel do pedido, metricas de
-- entrega, avaliacao e resumo de pagamento.
CREATE TABLE dim_order (
    order_id                       TEXT PRIMARY KEY,
    customer_id                    TEXT,
    order_status                   TEXT,
    order_purchase_timestamp       TEXT,
    purchase_date                  TEXT,
    order_delivered_customer_date  TEXT,
    order_estimated_delivery_date  TEXT,
    delivery_days                  INTEGER,   -- dias entre compra e entrega
    delay_days                     INTEGER,   -- positivo = atraso vs estimado
    on_time                        INTEGER,   -- 1 = entregue no prazo
    review_score                   INTEGER,   -- 1 a 5
    payment_value                  REAL,
    max_installments               INTEGER,
    payment_type                   TEXT,
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id)
);

-- Calendario.
CREATE TABLE dim_date (
    date_key    INTEGER PRIMARY KEY,   -- formato AAAAMMDD
    date        TEXT,
    year        INTEGER,
    quarter     INTEGER,
    month       INTEGER,
    month_name  TEXT,
    year_month  TEXT,
    day         INTEGER,
    weekday     INTEGER,               -- 0 = segunda
    is_weekend  INTEGER
);

-- ---------- FATO ----------

-- Grao: um item de pedido. Medidas aditivas: price e freight_value.
CREATE TABLE fact_order_items (
    order_id          TEXT,
    order_item_id     INTEGER,
    product_id        TEXT,
    seller_id         TEXT,
    customer_id       TEXT,
    date_key          INTEGER,
    price             REAL,
    freight_value     REAL,
    total_item_value  REAL,
    FOREIGN KEY (order_id)    REFERENCES dim_order(order_id),
    FOREIGN KEY (product_id)  REFERENCES dim_product(product_id),
    FOREIGN KEY (seller_id)   REFERENCES dim_seller(seller_id),
    FOREIGN KEY (customer_id) REFERENCES dim_customer(customer_id),
    FOREIGN KEY (date_key)    REFERENCES dim_date(date_key)
);
