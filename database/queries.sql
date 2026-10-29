-- Monthly completed net sales and gross profit.
SELECT DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS net_sales,
       SUM(oi.quantity * (oi.unit_price * (1 - oi.discount_percent / 100) - p.unit_cost)) AS gross_profit
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed'
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY sales_month;

-- Sales and margin by category.
SELECT p.category,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS net_sales,
       SUM(oi.quantity * (oi.unit_price * (1 - oi.discount_percent / 100) - p.unit_cost)) AS gross_profit
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed'
GROUP BY p.category
ORDER BY net_sales DESC;

-- Executive KPIs. Each order is counted once; returned and cancelled sales are excluded
-- because the current schema has no refund/return line-item model.
SELECT SUM(oi.quantity * oi.unit_price) AS gross_merchandise_value,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS net_merchandise_sales,
       SUM(oi.quantity * p.unit_cost) AS estimated_product_cost,
       SUM(oi.quantity * (oi.unit_price * (1 - oi.discount_percent / 100) - p.unit_cost)) AS estimated_gross_profit,
       COUNT(DISTINCT o.order_id) AS completed_orders,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100))
           / NULLIF(COUNT(DISTINCT o.order_id), 0) AS average_order_value
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed';

-- Customer lifetime completed-order spend and repeat purchase count.
SELECT c.customer_id, c.customer_name,
       COUNT(DISTINCT o.order_id) AS completed_orders,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS lifetime_net_sales
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
JOIN order_items AS oi ON oi.order_id = o.order_id
WHERE o.order_status = 'Completed'
GROUP BY c.customer_id, c.customer_name
ORDER BY lifetime_net_sales DESC;

-- Regional performance by shipping destination.
SELECT o.shipping_state,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS net_sales,
       COUNT(DISTINCT o.order_id) AS completed_orders,
       SUM(oi.quantity) AS units_sold
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
WHERE o.order_status = 'Completed'
GROUP BY o.shipping_state
ORDER BY net_sales DESC;

-- Average line-item discount and estimated gross margin by product category.
SELECT p.category,
       AVG(oi.discount_percent) AS average_discount_percent,
       SUM(oi.quantity * (oi.unit_price * (1 - oi.discount_percent / 100) - p.unit_cost))
           / NULLIF(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)), 0)
           AS estimated_gross_margin
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed'
GROUP BY p.category
ORDER BY estimated_gross_margin DESC;

-- Top 10 products by revenue and volume.
SELECT p.product_id, p.product_name, SUM(oi.quantity) AS units_sold,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS net_sales
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed'
GROUP BY p.product_id, p.product_name
ORDER BY net_sales DESC
LIMIT 10;

-- Customer-level RFM inputs (recency is relative to the latest completed order).
WITH customer_orders AS (
    SELECT o.customer_id, o.order_id, o.order_date,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS order_value
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id, o.order_id, o.order_date
)
SELECT c.customer_id, c.customer_name,
       DATEDIFF((SELECT MAX(order_date) FROM customer_orders), MAX(co.order_date)) AS recency_days,
       COUNT(DISTINCT co.order_id) AS purchase_frequency,
       SUM(co.order_value) AS monetary_value
FROM customer_orders AS co
JOIN customers AS c ON c.customer_id = co.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY monetary_value DESC;

-- Order lifecycle counts and rates.
SELECT order_status, COUNT(*) AS order_count,
       COUNT(*) / (SELECT COUNT(*) FROM orders) AS share_of_orders
FROM orders
GROUP BY order_status
ORDER BY order_count DESC;
