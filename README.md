# Dashboard no Power BI

Guia para reconstruir o painel a partir do modelo gerado pelo ETL. O objetivo é transformar o esquema estrela em um dashboard executivo de uma página.

## Conexão

Há dois caminhos:

1. **Via CSVs processados**: importar as tabelas de `data/processed/` (Obter Dados, Texto/CSV). Mais simples e sem dependência externa.
2. **Via SQLite**: conectar ao `data/olist.db` usando o conector ODBC do SQLite.

## Modelo de relacionamentos

Replicar o esquema estrela no modo de exibição de Modelo do Power BI:

* `fact_order_items[product_id]` para `dim_product[product_id]`
* `fact_order_items[seller_id]` para `dim_seller[seller_id]`
* `fact_order_items[customer_id]` para `dim_customer[customer_id]`
* `fact_order_items[date_key]` para `dim_date[date_key]`
* `fact_order_items[order_id]` para `dim_order[order_id]`

Todas as relações são de um para muitos, com a dimensão no lado um. Marcar `dim_date` como tabela de datas.

## Medidas DAX sugeridas

```DAX
Receita Total = SUM(fact_order_items[total_item_value])

Pedidos = DISTINCTCOUNT(fact_order_items[order_id])

Ticket Medio = DIVIDE([Receita Total], [Pedidos])

Pct No Prazo = AVERAGE(dim_order[on_time])

Nota Media = AVERAGE(dim_order[review_score])

Receita Mes Anterior =
CALCULATE([Receita Total], DATEADD(dim_date[date], -1, MONTH))

Crescimento MoM % =
DIVIDE([Receita Total] - [Receita Mes Anterior], [Receita Mes Anterior])
```

## Layout sugerido (uma página)

* Linha de cartões no topo: Receita Total, Pedidos, Ticket Médio, Nota Média.
* Gráfico de linha: receita por mês com a medida de crescimento.
* Barras horizontais: top 10 categorias por receita.
* Mapa ou barras: prazo médio de entrega por estado.
* Gráfico de colunas: nota média por faixa de atraso, o insight central do projeto.
* Segmentadores: ano, estado e categoria.

## Dashboard

<img width="1931" height="1174" alt="dashboard" src="https://github.com/user-attachments/assets/dde0f5e0-8a50-4d58-b2ca-bf0e2a2adf8c" />


## Boas práticas aplicadas

* Métricas como medidas DAX, nunca colunas calculadas desnecessárias.
* Tabela de calendário dedicada para inteligência de tempo.
* Nomes de campo limpos e em português na camada de apresentação.
