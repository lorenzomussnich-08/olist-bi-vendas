# Dicionário de dados

Esquema estrela gerado por `python/01_etl_build_model.py`. Grão da fato: um item de pedido.

## fact_order_items

| Coluna | Tipo | Descrição |
| :----- | :--- | :-------- |
| order_id | texto | Identificador do pedido. FK para dim_order. |
| order_item_id | inteiro | Sequência do item dentro do pedido. |
| product_id | texto | FK para dim_product. |
| seller_id | texto | FK para dim_seller. |
| customer_id | texto | FK para dim_customer. |
| date_key | inteiro | FK para dim_date, formato AAAAMMDD. |
| price | real | Valor do produto. Medida aditiva. |
| freight_value | real | Valor do frete do item. Medida aditiva. |
| total_item_value | real | price mais freight_value. |

## dim_order

| Coluna | Tipo | Descrição |
| :----- | :--- | :-------- |
| order_id | texto | Chave primária. |
| customer_id | texto | FK para dim_customer. |
| order_status | texto | Status: delivered, shipped, canceled, etc. |
| order_purchase_timestamp | texto | Data e hora da compra. |
| purchase_date | texto | Data da compra. |
| order_delivered_customer_date | texto | Data de entrega ao cliente. |
| order_estimated_delivery_date | texto | Data estimada de entrega. |
| delivery_days | inteiro | Dias entre compra e entrega. |
| delay_days | inteiro | Dias de atraso vs estimativa. Negativo significa adiantado. |
| on_time | inteiro | 1 quando entregue no prazo. |
| review_score | inteiro | Nota da avaliação, de 1 a 5. |
| payment_value | real | Valor total pago no pedido. |
| max_installments | inteiro | Maior número de parcelas do pedido. |
| payment_type | texto | Meio de pagamento principal. |

## dim_customer

| Coluna | Tipo | Descrição |
| :----- | :--- | :-------- |
| customer_id | texto | Chave de pedido. Chave primária. |
| customer_unique_id | texto | Identificador da pessoa real, usado para recorrência. |
| zip_prefix | inteiro | Prefixo do CEP. |
| city | texto | Cidade. |
| state | texto | Sigla do estado. |

## dim_product

| Coluna | Tipo | Descrição |
| :----- | :--- | :-------- |
| product_id | texto | Chave primária. |
| category_pt | texto | Categoria em português. |
| category_en | texto | Categoria em inglês. |
| weight_g | real | Peso em gramas. |
| product_length_cm | real | Comprimento. |
| product_height_cm | real | Altura. |
| product_width_cm | real | Largura. |

## dim_seller

| Coluna | Tipo | Descrição |
| :----- | :--- | :-------- |
| seller_id | texto | Chave primária. |
| zip_prefix | inteiro | Prefixo do CEP. |
| city | texto | Cidade. |
| state | texto | Sigla do estado. |

## dim_date

| Coluna | Tipo | Descrição |
| :----- | :--- | :-------- |
| date_key | inteiro | Chave primária, formato AAAAMMDD. |
| date | texto | Data. |
| year | inteiro | Ano. |
| quarter | inteiro | Trimestre. |
| month | inteiro | Mês. |
| month_name | texto | Nome curto do mês. |
| year_month | texto | Ano e mês no formato AAAA MM. |
| day | inteiro | Dia. |
| weekday | inteiro | Dia da semana, 0 igual segunda. |
| is_weekend | inteiro | 1 quando sábado ou domingo. |
