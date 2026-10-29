CREATE OR REPLACE VIEW v_sales_detail AS
SELECT o.order_id,
       oi.order_item_id,
       o.order_date,
       DATE(o.order_date) AS order_day,
       DATE_FORMAT(o.order_date, '%Y-%m') AS month_label,
       o.order_status,
       o.customer_id,
       c.customer_name,
       c.city AS customer_city,
       c.state AS customer_state,
       o.shipping_city,
       o.shipping_state,
       o.payment_method,
       p.product_id,
       p.product_name,
       p.category,
       oi.quantity,
       oi.unit_price,
       oi.discount_percent,
       p.unit_cost,
       oi.quantity * oi.unit_price AS gross_merchandise_value,
       oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100) AS net_sales,
       oi.quantity * p.unit_cost AS product_cost,
       oi.quantity * (oi.unit_price * (1 - oi.discount_percent / 100) - p.unit_cost) AS gross_profit
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
JOIN customers AS c ON c.customer_id = o.customer_id;

CREATE OR REPLACE VIEW v_monthly_sales AS
SELECT DATE_FORMAT(o.order_date, '%Y-%m') AS month_label,
       SUM(oi.quantity * oi.unit_price) AS gross_merchandise_value,
       SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS net_sales,
       SUM(oi.quantity * p.unit_cost) AS product_cost,
       SUM(oi.quantity * (oi.unit_price * (1 - oi.discount_percent / 100) - p.unit_cost)) AS gross_profit,
       COUNT(DISTINCT o.order_id) AS completed_orders,
       SUM(oi.quantity) AS units_sold
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed'
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m');

CREATE OR REPLACE VIEW v_customer_rfm AS
WITH completed_orders AS (
    SELECT o.customer_id, o.order_id, o.order_date,
           SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100)) AS order_value
    FROM orders AS o
    JOIN order_items AS oi ON oi.order_id = o.order_id
    WHERE o.order_status = 'Completed'
    GROUP BY o.customer_id, o.order_id, o.order_date
)
SELECT c.customer_id,
       c.customer_name,
       DATEDIFF((SELECT MAX(order_date) FROM completed_orders), MAX(co.order_date)) AS recency_days,
       COUNT(DISTINCT co.order_id) AS purchase_frequency,
       SUM(co.order_value) AS monetary_value
FROM completed_orders AS co
JOIN customers AS c ON c.customer_id = co.customer_id
GROUP BY c.customer_id, c.customer_name;
