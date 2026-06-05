#!/usr/bin/env bash
# Baixa os CSVs brutos do Olist a partir de um espelho publico no GitHub.
set -e
BASE="https://raw.githubusercontent.com/Ganesh7699/Brazilian-E-Commerce-OList/main"
cd "$(dirname "$0")"
for f in olist_customers_dataset.csv olist_order_items_dataset.csv \
         olist_order_payments_dataset.csv olist_order_reviews_dataset.csv \
         olist_orders_dataset.csv olist_products_dataset.csv \
         olist_sellers_dataset.csv product_category_name_translation.csv; do
  echo "Baixando $f ..."
  curl -s -L -o "$f" "$BASE/$f"
done
echo "Concluido."
