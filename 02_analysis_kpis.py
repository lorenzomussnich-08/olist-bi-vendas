"""
02_analysis_kpis.py
===================
Gera os principais KPIs e graficos do projeto a partir do banco SQLite
construido pelo ETL. As figuras alimentam o README e servem de base
para o dashboard em Power BI.

Uso:
    python 02_analysis_kpis.py
"""

from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "data" / "olist.db"
FIG = BASE / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# Paleta e estilo consistentes
PRIMARY = "#2563eb"
ACCENT = "#0f766e"
WARN = "#dc2626"
GRID = "#e5e7eb"
plt.rcParams.update({
    "figure.dpi": 120,
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
})


def reais(x, _):
    if x >= 1_000_000:
        return f"R$ {x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"R$ {x/1_000:.0f}k"
    return f"R$ {x:.0f}"


def q(con, sql):
    return pd.read_sql_query(sql, con)


def chart_monthly_revenue(con):
    df = q(con, """
        SELECT d.year_month, SUM(f.total_item_value) AS receita
        FROM fact_order_items f
        JOIN dim_order o ON o.order_id = f.order_id
        JOIN dim_date  d ON d.date_key = f.date_key
        WHERE o.order_status = 'delivered'
          AND d.year_month BETWEEN '2017-01' AND '2018-08'
        GROUP BY d.year_month ORDER BY d.year_month
    """)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(df["year_month"], df["receita"], marker="o", color=PRIMARY, lw=2)
    ax.fill_between(df["year_month"], df["receita"], alpha=0.08, color=PRIMARY)
    ax.set_title("Faturamento mensal (pedidos entregues)", fontweight="bold", loc="left")
    ax.yaxis.set_major_formatter(FuncFormatter(reais))
    ax.set_xticks(df["year_month"][::2])
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "01_faturamento_mensal.png", bbox_inches="tight")
    plt.close(fig)


def chart_top_categories(con):
    df = q(con, """
        SELECT p.category_en AS categoria, SUM(f.total_item_value) AS receita
        FROM fact_order_items f
        JOIN dim_product p ON p.product_id = f.product_id
        JOIN dim_order   o ON o.order_id   = f.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY p.category_en ORDER BY receita DESC LIMIT 10
    """).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh(df["categoria"], df["receita"], color=ACCENT)
    ax.set_title("Top 10 categorias por faturamento", fontweight="bold", loc="left")
    ax.xaxis.set_major_formatter(FuncFormatter(reais))
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(FIG / "02_top_categorias.png", bbox_inches="tight")
    plt.close(fig)


def chart_delay_vs_review(con):
    df = q(con, """
        SELECT
            CASE
                WHEN o.delay_days <= -5 THEN 'Adiantado 5+ d'
                WHEN o.delay_days <   0 THEN 'No prazo'
                WHEN o.delay_days =   0 THEN 'No limite'
                WHEN o.delay_days <=  5 THEN 'Atraso ate 5 d'
                ELSE 'Atraso 5+ d'
            END AS faixa,
            AVG(o.review_score) AS nota
        FROM dim_order o
        WHERE o.order_status='delivered' AND o.delay_days IS NOT NULL
          AND o.review_score IS NOT NULL
        GROUP BY faixa
    """)
    order = ["Adiantado 5+ d", "No prazo", "No limite", "Atraso ate 5 d", "Atraso 5+ d"]
    df = df.set_index("faixa").loc[order].reset_index()
    colors = [ACCENT, ACCENT, "#ca8a04", WARN, WARN]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bars = ax.bar(df["faixa"], df["nota"], color=colors)
    ax.bar_label(bars, fmt="%.2f", padding=3)
    ax.set_ylim(0, 5)
    ax.set_ylabel("Nota media (1 a 5)")
    ax.set_title("Pontualidade da entrega vs satisfacao do cliente",
                 fontweight="bold", loc="left")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(FIG / "03_atraso_vs_nota.png", bbox_inches="tight")
    plt.close(fig)


def chart_payment_mix(con):
    df = q(con, """
        SELECT o.payment_type AS tipo, COUNT(*) AS pedidos
        FROM dim_order o
        WHERE o.order_status='delivered' AND o.payment_type IS NOT NULL
        GROUP BY o.payment_type ORDER BY pedidos DESC
    """)
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    wedges, _, autotxt = ax.pie(
        df["pedidos"], labels=df["tipo"], autopct="%1.1f%%",
        colors=[PRIMARY, ACCENT, "#ca8a04", "#9333ea"], startangle=90,
        wedgeprops=dict(width=0.42, edgecolor="white"))
    for t in autotxt:
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title("Mix de meios de pagamento", fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIG / "04_meios_pagamento.png", bbox_inches="tight")
    plt.close(fig)


def print_kpis(con):
    kpi = q(con, """
        SELECT COUNT(DISTINCT f.order_id) AS pedidos,
               ROUND(SUM(f.total_item_value),2) AS receita,
               ROUND(SUM(f.total_item_value)/COUNT(DISTINCT f.order_id),2) AS ticket
        FROM fact_order_items f JOIN dim_order o ON o.order_id=f.order_id
        WHERE o.order_status='delivered'
    """).iloc[0]
    print("\n=== KPIs principais ===")
    print(f"Pedidos entregues : {int(kpi.pedidos):,}")
    print(f"Receita total     : R$ {kpi.receita:,.2f}")
    print(f"Ticket medio      : R$ {kpi.ticket:,.2f}")


def main():
    con = sqlite3.connect(DB_PATH)
    chart_monthly_revenue(con)
    chart_top_categories(con)
    chart_delay_vs_review(con)
    chart_payment_mix(con)
    print_kpis(con)
    con.close()
    print(f"\nGraficos salvos em {FIG}")


if __name__ == "__main__":
    main()
