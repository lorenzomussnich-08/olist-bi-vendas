"""
01_etl_build_model.py
======================
Pipeline de ETL do projeto Olist BI.

Lê os CSVs brutos do Olist, limpa os dados, modela um esquema estrela
(tabelas fato e dimensao) e carrega o resultado em um banco SQLite pronto
para ser consultado com SQL e conectado ao Power BI.

Grao da tabela fato (fact_order_items): um item de pedido.
Dimensoes: dim_customer, dim_product, dim_seller, dim_date, dim_order.

Uso:
    python 01_etl_build_model.py
"""

from pathlib import Path
import sqlite3
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
DB_PATH = BASE / "data" / "olist.db"
PROCESSED.mkdir(parents=True, exist_ok=True)


def load_raw():
    """Carrega os CSVs brutos em dataframes."""
    print("Lendo CSVs brutos...")
    return {
        "customers": pd.read_csv(RAW / "olist_customers_dataset.csv"),
        "orders": pd.read_csv(RAW / "olist_orders_dataset.csv"),
        "items": pd.read_csv(RAW / "olist_order_items_dataset.csv"),
        "payments": pd.read_csv(RAW / "olist_order_payments_dataset.csv"),
        "reviews": pd.read_csv(RAW / "olist_order_reviews_dataset.csv"),
        "products": pd.read_csv(RAW / "olist_products_dataset.csv"),
        "sellers": pd.read_csv(RAW / "olist_sellers_dataset.csv"),
        "cat": pd.read_csv(RAW / "product_category_name_translation.csv"),
    }


def build_dim_customer(d):
    """Dimensao de clientes. Padroniza cidade e estado."""
    df = d["customers"].copy()
    df["customer_city"] = df["customer_city"].str.title().str.strip()
    df["customer_state"] = df["customer_state"].str.upper().str.strip()
    df = df.rename(columns={
        "customer_zip_code_prefix": "zip_prefix",
        "customer_city": "city",
        "customer_state": "state",
    })
    return df[["customer_id", "customer_unique_id", "zip_prefix", "city", "state"]]


def build_dim_product(d):
    """Dimensao de produtos com categoria traduzida para o ingles."""
    prod = d["products"].copy()
    cat = d["cat"].copy()
    prod = prod.merge(cat, on="product_category_name", how="left")
    prod["product_category_name"] = prod["product_category_name"].fillna("indefinido")
    prod["product_category_name_english"] = (
        prod["product_category_name_english"].fillna("undefined")
    )
    prod = prod.rename(columns={
        "product_category_name": "category_pt",
        "product_category_name_english": "category_en",
        "product_weight_g": "weight_g",
    })
    cols = ["product_id", "category_pt", "category_en", "weight_g",
            "product_length_cm", "product_height_cm", "product_width_cm"]
    return prod[cols]


def build_dim_seller(d):
    """Dimensao de vendedores."""
    df = d["sellers"].copy()
    df["seller_city"] = df["seller_city"].str.title().str.strip()
    df["seller_state"] = df["seller_state"].str.upper().str.strip()
    df = df.rename(columns={
        "seller_zip_code_prefix": "zip_prefix",
        "seller_city": "city",
        "seller_state": "state",
    })
    return df[["seller_id", "zip_prefix", "city", "state"]]


def build_dim_order(d):
    """
    Dimensao de pedidos. Junta status, datas de entrega, avaliacao e
    pagamento agregado por pedido. Calcula metricas de prazo de entrega.
    """
    orders = d["orders"].copy()
    date_cols = [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for c in date_cols:
        orders[c] = pd.to_datetime(orders[c], errors="coerce")

    # Tempo de entrega real e atraso frente ao estimado (em dias)
    orders["delivery_days"] = (
        orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
    ).dt.days
    orders["delay_days"] = (
        orders["order_delivered_customer_date"] - orders["order_estimated_delivery_date"]
    ).dt.days
    orders["on_time"] = (orders["delay_days"] <= 0).where(
        orders["order_delivered_customer_date"].notna()
    )

    # Avaliacao: mantem a primeira nota por pedido
    reviews = (
        d["reviews"].sort_values("review_creation_date")
        .drop_duplicates("order_id", keep="first")[["order_id", "review_score"]]
    )

    # Pagamento agregado por pedido: valor total, parcelas e tipo principal
    pay = d["payments"].copy()
    pay_agg = pay.groupby("order_id").agg(
        payment_value=("payment_value", "sum"),
        max_installments=("payment_installments", "max"),
    ).reset_index()
    main_type = (
        pay.sort_values("payment_value", ascending=False)
        .drop_duplicates("order_id", keep="first")[["order_id", "payment_type"]]
    )
    pay_agg = pay_agg.merge(main_type, on="order_id", how="left")

    out = (
        orders.merge(reviews, on="order_id", how="left")
        .merge(pay_agg, on="order_id", how="left")
    )
    out["purchase_date"] = out["order_purchase_timestamp"].dt.date
    keep = [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "purchase_date", "order_delivered_customer_date",
        "order_estimated_delivery_date", "delivery_days", "delay_days",
        "on_time", "review_score", "payment_value", "max_installments",
        "payment_type",
    ]
    return out[keep]


def build_dim_date(fact_dates):
    """Dimensao de calendario derivada das datas de compra presentes na fato."""
    dates = pd.to_datetime(pd.Series(fact_dates).dropna().unique())
    df = pd.DataFrame({"date": dates}).sort_values("date").reset_index(drop=True)
    meses = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
    }
    df["date_key"] = df["date"].dt.strftime("%Y%m%d").astype(int)
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["month"] = df["date"].dt.month
    df["month_name"] = df["month"].map(meses)
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    df["day"] = df["date"].dt.day
    df["weekday"] = df["date"].dt.dayofweek  # 0 = segunda
    df["is_weekend"] = df["weekday"].isin([5, 6])
    df["date"] = df["date"].dt.date
    return df[["date_key", "date", "year", "quarter", "month", "month_name",
               "year_month", "day", "weekday", "is_weekend"]]


def build_fact(d, dim_order):
    """
    Tabela fato no grao de item de pedido.
    Medidas aditivas: price e freight_value.
    """
    items = d["items"].copy()
    # Liga cada item ao cliente e a data de compra via dim_order
    order_lookup = dim_order[["order_id", "customer_id", "purchase_date"]]
    fact = items.merge(order_lookup, on="order_id", how="left")
    fact["purchase_date"] = pd.to_datetime(fact["purchase_date"], errors="coerce")
    fact["date_key"] = fact["purchase_date"].dt.strftime("%Y%m%d")
    fact["total_item_value"] = fact["price"] + fact["freight_value"]
    fact = fact.dropna(subset=["date_key"])
    fact["date_key"] = fact["date_key"].astype(int)
    keep = [
        "order_id", "order_item_id", "product_id", "seller_id", "customer_id",
        "date_key", "price", "freight_value", "total_item_value",
    ]
    return fact[keep]


def quality_report(tables):
    """Pequeno relatorio de qualidade impresso no console."""
    print("\n=== Relatorio de qualidade ===")
    for name, df in tables.items():
        nulos = int(df.isna().sum().sum())
        print(f"{name:16s} linhas={len(df):>7}  colunas={df.shape[1]:>2}  nulos={nulos}")


def main():
    d = load_raw()

    dim_customer = build_dim_customer(d)
    dim_product = build_dim_product(d)
    dim_seller = build_dim_seller(d)
    dim_order = build_dim_order(d)
    fact = build_fact(d, dim_order)
    dim_date = build_dim_date(dim_order["purchase_date"])

    tables = {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_seller": dim_seller,
        "dim_order": dim_order,
        "dim_date": dim_date,
        "fact_order_items": fact,
    }

    quality_report(tables)

    # Salva CSVs processados
    print("\nSalvando CSVs processados...")
    for name, df in tables.items():
        df.to_csv(PROCESSED / f"{name}.csv", index=False)

    # Carrega no SQLite
    print(f"Carregando no SQLite em {DB_PATH} ...")
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    for name, df in tables.items():
        df.to_sql(name, con, if_exists="replace", index=False)
    # Indices para acelerar os joins do esquema estrela
    cur = con.cursor()
    cur.executescript(
        """
        CREATE INDEX idx_fact_product ON fact_order_items(product_id);
        CREATE INDEX idx_fact_seller  ON fact_order_items(seller_id);
        CREATE INDEX idx_fact_cust    ON fact_order_items(customer_id);
        CREATE INDEX idx_fact_date    ON fact_order_items(date_key);
        CREATE INDEX idx_order_id     ON dim_order(order_id);
        """
    )
    con.commit()
    con.close()
    print("ETL concluido com sucesso.")


if __name__ == "__main__":
    main()
