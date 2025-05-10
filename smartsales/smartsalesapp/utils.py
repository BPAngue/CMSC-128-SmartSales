import pandas as pd
from datetime import datetime, timedelta
from django.db.models import Sum
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_percentage_error
from .models import Transaction

def get_date_range(period: str):
    today = datetime.now().date()
    if period == 'daily':
        start_date = today
    elif period == 'weekly':
        start_date = today - timedelta(days=today.weekday())
    elif period == 'monthly':
        start_date = today.replace(day=1)
    else:
        start_date = today.replace(day=1)
    return start_date, today

def prepare_sales_dataframe(transactions_qs):
    sales_data = (
        transactions_qs
        .values('date_of_transaction')
        .annotate(total=Sum('total_amount'))
        .order_by('date_of_transaction')
    )
    df = pd.DataFrame(list(sales_data))
    if df.empty:
        return None

    df['date_of_transaction'] = pd.to_datetime(df['date_of_transaction'])
    df.set_index('date_of_transaction', inplace=True)
    df['total'] = df['total'].astype(float)
    df = df.asfreq('D').fillna(0).rename(columns={'total': 'total_sales'})

    # Require at least 5 days with non-zero sales to attempt ARIMA
    if (df['total_sales'] > 0).sum() < 5:
        return None

    return df

def arima_forecast(series, steps: int = 30, order=(1, 1, 1)):
    if series.empty:
        return pd.Series([0.0] * steps), 0.0, 0.0

    train_size = int(len(series) * 0.8)
    train, test = series.iloc[:train_size], series.iloc[train_size:]

    try:
        model = ARIMA(train, order=order)
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=steps)

        if len(test) > 0 and (test != 0).any():
            preds = model_fit.predict(start=test.index[0], end=test.index[-1])
            mape = mean_absolute_percentage_error(test, preds)
            accuracy = round(max(0.0, (1 - mape) * 100), 2)
        else:
            accuracy = 100.0

        return forecast.astype(float), float(series.sum()), accuracy

    except Exception:
        # If ARIMA fails, fallback to SMA
        fallback_value = series.mean() if not series.empty else 0.0
        forecast = pd.Series([fallback_value] * steps)
        return forecast, float(series.sum()), 0.0  # Fallback accuracy is 0%

def growth_pct(current: float, previous: float) -> float:
    return round(((current - previous) / previous) * 100, 2) if previous else 0.0

def multi_horizon_forecasts(series, horizons=(1, 7, 30)):
    results = {}
    forecast, _, _ = arima_forecast(series, steps=max(horizons))
    for h in horizons:
        results[h] = float(forecast.iloc[:h].sum())
    return results

def calculate_sales_data(period: str):
    start_date, end_date = get_date_range(period)
    transactions_qs = Transaction.objects.filter(date_of_transaction__range=[start_date, end_date])

    sales_total = transactions_qs.aggregate(total=Sum('total_amount'))['total'] or 0

    top_product_data = (transactions_qs
        .values('product__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')
        .first())

    top_product = {
        'name': top_product_data['product__name'] if top_product_data else 'N/A',
        'total_sold': top_product_data['total_sold'] if top_product_data else 0
    }

    return sales_total, top_product