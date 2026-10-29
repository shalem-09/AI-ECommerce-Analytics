# Data dictionary

## Source tables

- `customers`: customer profile, location, and signup date; `customer_id` is the primary key.
- `products`: product category, current unit cost/price, and stock; `product_id` is the primary key.
- `orders`: customer, timestamp, status, payment method, and shipping destination; `order_id` is the primary key.
- `order_items`: order line, product, quantity, transaction unit price, and discount percentage; `order_item_id` is the primary key.

## Reporting views

- `v_sales_detail`: one row per order line with order, customer, and product attributes. `gross_merchandise_value` is quantity × transaction unit price before discounts. `net_sales` applies the line discount. `product_cost` is quantity × current product unit cost, and `gross_profit` is net sales less that estimated cost.
- `v_monthly_sales`: completed-order monthly GMV, net sales, estimated product cost, estimated gross profit, distinct completed order count, and units.
- `v_customer_rfm`: completed-buyer recency, frequency, and monetary inputs. Recency is measured from the latest completed order in the dataset, not the current date.

## Business rules

Status values are `Completed`, `Cancelled`, `Returned`, `Shipped`, and `Pending`. Sales, costs, and estimated gross profit include only `Completed` orders; lifecycle counts include all statuses. AOV is completed net merchandise sales divided by distinct completed orders with eligible order lines. Repeat-customer rate is repeat completed buyers divided by all completed buyers.

The schema has no return/refund line-item model, so returned orders are excluded from completed sales without estimating a refund. `gross_profit` is an estimate based on current product cost, not historical COGS or net profit. Currency is not stored as a column; configure source data consistently and set display formatting to match its currency.
