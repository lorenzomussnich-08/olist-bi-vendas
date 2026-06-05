-- ============================================================
-- 02_analysis.sql
-- Perguntas de negocio respondidas com SQL sobre o esquema estrela.
-- ------------------------------------------------------------
-- Cada bloco e uma pergunta de negocio independente. As consultas
-- usam JOINs sobre o esquema estrela, CTEs, funcoes de janela
-- (LAG, RANK, NTILE, SUM OVER) e CASE.
-- Banco de referencia: SQLite (data/olist.db).
-- ============================================================


-- ------------------------------------------------------------
-- Q1. Visao geral: faturamento, pedidos e ticket medio
-- ------------------------------------------------------------
-- Considera apenas pedidos entregues, para nao inflar com pedidos
-- cancelados ou indisponiveis.
SELECT
    COUNT(DISTINCT f.order_id)                       AS pedidos,
    ROUND(SUM(f.price), 2)                           AS receita_produtos,
    ROUND(SUM(f.freight_value), 2)                   AS receita_frete,
    ROUND(SUM(f.total_item_value), 2)                AS receita_total,
    ROUND(SUM(f.total_item_value)
          / COUNT(DISTINCT f.order_id), 2)           AS ticket_medio
FROM fact_order_items f
JOIN dim_order o ON o.order_id = f.order_id
WHERE o.order_status = 'delivered';


-- ------------------------------------------------------------
-- Q2. Evolucao mensal do faturamento com crescimento MoM
-- ------------------------------------------------------------
-- Usa LAG para comparar cada mes com o anterior.
WITH receita_mensal AS (
    SELECT
        d.year_month,
        SUM(f.total_item_value) AS receita
    FROM fact_order_items f
    JOIN dim_order o ON o.order_id = f.order_id
    JOIN dim_date  d ON d.date_key = f.date_key
    WHERE o.order_status = 'delivered'
    GROUP BY d.year_month
)
SELECT
    year_month,
    ROUND(receita, 2)                                          AS receita,
    ROUND(LAG(receita) OVER (ORDER BY year_month), 2)          AS receita_mes_anterior,
    ROUND(100.0 * (receita - LAG(receita) OVER (ORDER BY year_month))
          / LAG(receita) OVER (ORDER BY year_month), 1)        AS crescimento_pct
FROM receita_mensal
ORDER BY year_month;


-- ------------------------------------------------------------
-- Q3. Top 10 categorias por faturamento e participacao no total
-- ------------------------------------------------------------
-- SUM OVER () calcula o total geral sem segundo agrupamento.
WITH por_categoria AS (
    SELECT
        p.category_en,
        SUM(f.total_item_value) AS receita,
        COUNT(*)                AS itens
    FROM fact_order_items f
    JOIN dim_product p ON p.product_id = f.product_id
    JOIN dim_order   o ON o.order_id   = f.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.category_en
)
SELECT
    category_en,
    ROUND(receita, 2)                                         AS receita,
    itens,
    ROUND(100.0 * receita / SUM(receita) OVER (), 1)          AS pct_do_total,
    RANK() OVER (ORDER BY receita DESC)                       AS posicao
FROM por_categoria
ORDER BY receita DESC
LIMIT 10;


-- ------------------------------------------------------------
-- Q4. Curva de Pareto: participacao acumulada por categoria
-- ------------------------------------------------------------
-- SUM OVER (ORDER BY ...) gera o acumulado para responder se
-- 20% das categorias concentram 80% da receita.
WITH por_categoria AS (
    SELECT p.category_en, SUM(f.total_item_value) AS receita
    FROM fact_order_items f
    JOIN dim_product p ON p.product_id = f.product_id
    GROUP BY p.category_en
)
SELECT
    category_en,
    ROUND(receita, 2)                                         AS receita,
    ROUND(100.0 *
        SUM(receita) OVER (ORDER BY receita DESC)
        / SUM(receita) OVER (), 1)                            AS pct_acumulado
FROM por_categoria
ORDER BY receita DESC;


-- ------------------------------------------------------------
-- Q5. Segmentacao RFM de clientes
-- ------------------------------------------------------------
-- Recencia, frequencia e valor monetario por cliente real
-- (customer_unique_id), com NTILE para criar quartis 1 a 4.
WITH base AS (
    SELECT
        c.customer_unique_id,
        MAX(o.purchase_date)        AS ultima_compra,
        COUNT(DISTINCT f.order_id)  AS frequencia,
        SUM(f.total_item_value)     AS valor
    FROM fact_order_items f
    JOIN dim_order    o ON o.order_id    = f.order_id
    JOIN dim_customer c ON c.customer_id = f.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
scores AS (
    SELECT
        customer_unique_id,
        frequencia,
        ROUND(valor, 2) AS valor,
        NTILE(4) OVER (ORDER BY ultima_compra DESC) AS r_score,
        NTILE(4) OVER (ORDER BY frequencia ASC)     AS f_score,
        NTILE(4) OVER (ORDER BY valor ASC)          AS m_score
    FROM base
)
SELECT
    CASE
        WHEN r_score >= 3 AND m_score >= 3 THEN 'Alto valor'
        WHEN r_score >= 3 AND m_score <  3 THEN 'Recente em desenvolvimento'
        WHEN r_score <  3 AND m_score >= 3 THEN 'Em risco de churn'
        ELSE 'Baixo engajamento'
    END                                AS segmento,
    COUNT(*)                           AS clientes,
    ROUND(AVG(valor), 2)               AS valor_medio
FROM scores
GROUP BY segmento
ORDER BY valor_medio DESC;


-- ------------------------------------------------------------
-- Q6. Logistica: prazo de entrega e pontualidade por estado
-- ------------------------------------------------------------
SELECT
    c.state,
    COUNT(*)                                          AS pedidos,
    ROUND(AVG(o.delivery_days), 1)                    AS dias_entrega_medio,
    ROUND(100.0 * AVG(o.on_time), 1)                  AS pct_no_prazo,
    ROUND(AVG(o.review_score), 2)                     AS nota_media
FROM dim_order o
JOIN dim_customer c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
  AND o.delivery_days IS NOT NULL
GROUP BY c.state
HAVING COUNT(*) >= 100
ORDER BY dias_entrega_medio DESC;


-- ------------------------------------------------------------
-- Q7. Impacto do atraso na satisfacao do cliente
-- ------------------------------------------------------------
-- Agrupa pedidos por faixa de pontualidade e mede a nota media.
SELECT
    CASE
        WHEN o.delay_days <= -5 THEN 'Adiantado 5+ dias'
        WHEN o.delay_days <   0 THEN 'No prazo'
        WHEN o.delay_days =   0 THEN 'No limite'
        WHEN o.delay_days <=  5 THEN 'Atraso ate 5 dias'
        ELSE 'Atraso acima de 5 dias'
    END                                AS faixa_entrega,
    COUNT(*)                           AS pedidos,
    ROUND(AVG(o.review_score), 2)      AS nota_media
FROM dim_order o
WHERE o.order_status = 'delivered'
  AND o.delay_days   IS NOT NULL
  AND o.review_score IS NOT NULL
GROUP BY faixa_entrega
ORDER BY nota_media DESC;


-- ------------------------------------------------------------
-- Q8. Comportamento de pagamento: tipo, parcelamento e ticket
-- ------------------------------------------------------------
SELECT
    o.payment_type,
    COUNT(*)                           AS pedidos,
    ROUND(AVG(o.payment_value), 2)     AS ticket_medio,
    ROUND(AVG(o.max_installments), 1)  AS parcelas_medias,
    ROUND(100.0 * COUNT(*)
          / SUM(COUNT(*)) OVER (), 1)  AS pct_pedidos
FROM dim_order o
WHERE o.order_status = 'delivered'
  AND o.payment_type IS NOT NULL
GROUP BY o.payment_type
ORDER BY pedidos DESC;


-- ------------------------------------------------------------
-- Q9. Top 10 vendedores por faturamento
-- ------------------------------------------------------------
SELECT
    f.seller_id,
    s.state,
    COUNT(DISTINCT f.order_id)                       AS pedidos,
    ROUND(SUM(f.total_item_value), 2)                AS receita,
    DENSE_RANK() OVER (ORDER BY SUM(f.total_item_value) DESC) AS ranking
FROM fact_order_items f
JOIN dim_seller s ON s.seller_id = f.seller_id
JOIN dim_order  o ON o.order_id  = f.order_id
WHERE o.order_status = 'delivered'
GROUP BY f.seller_id, s.state
ORDER BY receita DESC
LIMIT 10;


-- ------------------------------------------------------------
-- Q10. Clientes recorrentes vs unicos
-- ------------------------------------------------------------
-- Mede quantos clientes reais compraram mais de uma vez e o quanto
-- representam da receita, indicador chave de fidelizacao.
WITH compras AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT f.order_id) AS pedidos,
        SUM(f.total_item_value)    AS receita
    FROM fact_order_items f
    JOIN dim_order    o ON o.order_id    = f.order_id
    JOIN dim_customer c ON c.customer_id = f.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT
    CASE WHEN pedidos > 1 THEN 'Recorrente' ELSE 'Unico' END AS tipo_cliente,
    COUNT(*)                                                 AS clientes,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)       AS pct_clientes,
    ROUND(SUM(receita), 2)                                   AS receita,
    ROUND(100.0 * SUM(receita) / SUM(SUM(receita)) OVER (), 1) AS pct_receita
FROM compras
GROUP BY tipo_cliente;
