# AI-Powered E-Commerce Sales Analytics & Business Intelligence Platform

Continue the existing project as a MySQL-backed analytics platform. It combines a Streamlit dashboard, pandas/NumPy analytics, scikit-learn forecasting, deterministic demo data, read-only business insights, and Power BI source assets.

## Features and architecture

- `database\schema.sql`: normalized MySQL Community Server schema; `database\connection.py` reads credentials from `.env` and loads only the four MySQL source tables.
- `analytics\`: data cleaning, KPI calculations, SQL/Pandas sales summaries, RFM customer scoring, and time-series forecasting.
- `app.py`: dark navy Streamlit dashboard with executive, sales, product, customer, regional, forecast, data-quality, and assistant views.
- `ai\assistant.py`: local, database-backed answer templates. It does not execute user-supplied SQL or require an API key.
- `powerbi\`: SQL views, DAX, Power Query M, a data dictionary, and report layout instructions.
- `tests\`: deterministic unit tests; the optional MySQL integration test is enabled only on request.

The application database is MySQL only. If MySQL cannot be reached, the dashboard shows a connection error and no live-data substitute. The in-memory synthetic data mode is available only when explicitly selected with `USE_MYSQL=false`.

## Technology

Python 3.11+, MySQL Community Server 8+, SQLAlchemy/PyMySQL, Pandas, NumPy, Streamlit, Plotly, scikit-learn, pytest, and Power BI Desktop with a MySQL connector.

## Windows setup

From PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` in a text editor with your local MySQL host, port, database, user, and password. The app and scripts load this file; they do not print or overwrite it. `.env` is ignored by Git. Never paste credentials into source code, Power Query, or a commit.

Apply the non-destructive schema to your chosen database:

```powershell
Get-Content .\database\schema.sql | mysql -u root -p
```

The schema creates `ecommerce_analytics` if needed and uses `CREATE TABLE IF NOT EXISTS`. It does not drop tables or alter/delete rows.

### Safe sample data

Sample rows are **not loaded automatically**. To keep demo rows separate from a real/business database, the seeder accepts only an explicitly named database ending in `_demo` and requires an explicit confirmation flag. It creates the schema there, inserts only when all four tables are empty, and recognizes a complete prior demo load on rerun. It refuses to add rows to a partially populated or unrecognized database.

```powershell
python -m database.seed_mysql_demo --database ecommerce_analytics_demo --confirm-demo-data
```

The script uses the host/port/user/password in `.env`, but targets only the database named by `--database`. After loading, point the app to `ecommerce_analytics_demo` by editing `DB_NAME` in `.env`, then restart the app. Expected counts are 500 customers, 100 products, 2,000 orders, and 5,000 order items; rely on the script's printed post-load counts to verify an actual run.

Do not run the seeder against a production/business database. If you do not explicitly configure a demo database, use your existing data or leave the database empty.

## Run the application

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

By default Streamlit opens `http://localhost:8501`. Use **Refresh data** after changing the database contents or environment settings. The dashboard's read path is limited to `SELECT` queries.

To run against the separately seeded demo database without editing `.env`, override only the current PowerShell process:

```powershell
$env:DB_NAME = 'ecommerce_analytics_demo'
streamlit run app.py
Remove-Item Env:DB_NAME
```

## Analytics definitions

- GMV = quantity × transaction unit price before discounts.
- Net merchandise sales = quantity × transaction unit price × (1 − discount percent / 100).
- Estimated product cost = quantity × current product unit cost.
- Estimated gross profit = net merchandise sales − estimated product cost; this is **not net profit** and cost is not historical COGS.
- Completed sales, AOV, product/category/region performance, and forecast history exclude non-completed orders. AOV uses completed orders with eligible order lines.
- The schema has no return/refund line-item model. `Returned` orders are excluded from completed sales and remain visible in lifecycle analysis; no refund amount is inferred.
- Repeat customer rate is completed-order buyers with more than one completed order divided by all completed-order buyers.
- RFM recency is relative to the latest completed purchase in the selected dataset. Frequency is distinct completed orders; monetary value is net merchandise sales. Scores are within-dataset quintile ranks; non-buyers are labeled `No purchases`.
- Forecasts are monthly completed net sales. A chronological holdout split compares linear regression against a last-observed-month baseline; MAE, RMSE, and non-zero-only MAPE are reported. This is an estimate, not a guarantee.

`database\queries.sql` contains read-only SQL examples. SQL reporting views and Power BI measures use the same completed-sale definitions.

## Tests and checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe .\scripts\validate_project.py
```

To opt into read-only MySQL integration checks, set `$env:RUN_MYSQL_INTEGRATION_TESTS = '1'` and run pytest. These checks do not seed or modify data.

## Power BI

Power BI Desktop is not automated by this project and no `.pbix` is included. See [Power BI setup](./powerbi/README.md), [SQL views](./powerbi/sql_views.sql), [DAX measures](./powerbi/dax_measures.dax), [Power Query M](./powerbi/power_query_m_code.txt), [data dictionary](./powerbi/data_dictionary.md), and [dashboard design](./powerbi/dashboard_design.md). Install the appropriate MySQL connector for your Power BI version and supply credentials through Power BI's data-source credential UI.

## Troubleshooting

- **MySQL connection refused / access denied:** verify the MySQL service, host/port, database, user grants, and `.env` settings. The displayed connection error does not include the configured password.
- **Empty dashboard:** verify `DB_NAME`, schema/table presence, and table row counts. The dashboard intentionally does not invent fallback business metrics.
- **Seeder refuses to load:** it requires an explicitly named `*_demo` database and empty tables (or the recognized complete demo dataset). Investigate partial/real data rather than deleting it.
- **Streamlit command not found:** activate `.venv` or use `.\.venv\Scripts\python.exe -m streamlit run app.py`.
- **Power BI cannot connect:** confirm the MySQL connector bitness/version and grant read access to the reporting views.

## Screenshots

No dashboard screenshots are currently present in `assets\`.
