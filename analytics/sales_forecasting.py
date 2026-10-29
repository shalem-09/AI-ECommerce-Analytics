from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


FORECAST_COLUMNS = [
    "period",
    "actual",
    "predicted",
    "model",
    "mae",
    "rmse",
    "mape",
    "baseline_model",
    "baseline_mae",
    "baseline_rmse",
]


def build_forecast_summary(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    products: pd.DataFrame,
    horizon: int = 3,
) -> pd.DataFrame:
    if orders.empty or order_items.empty or products.empty:
        return pd.DataFrame(columns=FORECAST_COLUMNS)
    if horizon < 1:
        raise ValueError("Forecast horizon must be at least one month.")

    merged = order_items.merge(
        products[["product_id"]], on="product_id", how="inner"
    ).merge(
        orders[["order_id", "order_status", "order_date"]],
        on="order_id",
        how="inner",
    )
    merged["order_date"] = pd.to_datetime(merged["order_date"], errors="coerce")
    merged["quantity"] = pd.to_numeric(merged["quantity"], errors="coerce").fillna(0)
    merged["unit_price"] = pd.to_numeric(merged["unit_price"], errors="coerce").fillna(0)
    merged["discount_percent"] = pd.to_numeric(
        merged["discount_percent"], errors="coerce"
    ).fillna(0)
    completed = merged[merged["order_status"] == "Completed"].dropna(
        subset=["order_date"]
    )
    if completed.empty:
        return pd.DataFrame(columns=FORECAST_COLUMNS)

    completed["net_sales"] = (
        completed["quantity"]
        * completed["unit_price"]
        * (1 - completed["discount_percent"] / 100)
    )
    monthly_sales = completed.groupby(
        completed["order_date"].dt.to_period("M")
    )["net_sales"].sum()
    full_months = pd.period_range(
        monthly_sales.index.min(), monthly_sales.index.max(), freq="M"
    )
    actuals = monthly_sales.reindex(full_months, fill_value=0).astype(float)
    values = actuals.to_numpy()
    if len(values) < 3:
        return pd.DataFrame(columns=FORECAST_COLUMNS)
    positions = np.arange(len(values)).reshape(-1, 1)

    validation_count = min(max(1, len(values) // 5), len(values) - 2)
    split = len(values) - validation_count
    validation_model = LinearRegression().fit(positions[:split], values[:split])
    validation_predictions = validation_model.predict(positions[split:])
    validation_actuals = values[split:]
    mae = float(mean_absolute_error(validation_actuals, validation_predictions))
    rmse = float(mean_squared_error(validation_actuals, validation_predictions) ** 0.5)
    nonzero_actuals = validation_actuals != 0
    mape = (
        float(
            np.mean(
                np.abs(
                    (validation_actuals[nonzero_actuals]
                     - validation_predictions[nonzero_actuals])
                    / validation_actuals[nonzero_actuals]
                )
            ) * 100
        )
        if nonzero_actuals.any()
        else float("nan")
    )
    baseline_predictions = np.full(validation_count, values[split - 1])
    baseline_mae = float(mean_absolute_error(validation_actuals, baseline_predictions))
    baseline_rmse = float(
        mean_squared_error(validation_actuals, baseline_predictions) ** 0.5
    )

    model = LinearRegression().fit(positions, values)
    future_positions = np.arange(len(values), len(values) + horizon).reshape(-1, 1)
    future_predictions = np.maximum(model.predict(future_positions), 0)
    forecast_periods = pd.period_range(
        actuals.index[-1] + 1, periods=horizon, freq="M"
    )
    metrics = {
        "model": "LinearRegression",
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "baseline_model": "Last observed month",
        "baseline_mae": baseline_mae,
        "baseline_rmse": baseline_rmse,
    }
    history = pd.DataFrame(
        {
            "period": actuals.index.astype(str),
            "actual": values,
            "predicted": np.nan,
            **{key: value for key, value in metrics.items()},
        }
    )
    history.loc[history.index[split:], "predicted"] = validation_predictions
    future = pd.DataFrame(
        {
            "period": forecast_periods.astype(str),
            "actual": np.nan,
            "predicted": future_predictions,
            **{key: value for key, value in metrics.items()},
        }
    )
    return pd.concat([history, future], ignore_index=True)[FORECAST_COLUMNS]
