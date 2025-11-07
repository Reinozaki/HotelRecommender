# predict_bookings.py (fixed for exactly 3 months)
import mysql.connector
import pandas as pd
import json
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from datetime import datetime, timedelta
import os
import calendar

# --- Database Connection ---
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="hotel_system"
)
cursor = conn.cursor()
cursor.execute("SELECT check_in FROM reservations")
rows = cursor.fetchall()
conn.close()

if not rows:
    print("No reservations found.")
    exit()

# Convert to DataFrame
df = pd.DataFrame(rows, columns=['check_in'])
df['check_in'] = pd.to_datetime(df['check_in'])

# Extract features
df['year'] = df['check_in'].dt.year
df['month'] = df['check_in'].dt.month
df['day'] = df['check_in'].dt.day
df['weekday'] = df['check_in'].dt.dayofweek

# Aggregate daily bookings
daily_bookings = df.groupby(['year','month','day','weekday']).size().reset_index(name='bookings')
X = daily_bookings[['year','month','day','weekday']]
y = daily_bookings['bookings']

# Train Random Forest Regressor
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestRegressor(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

# --- Predict next 3 months based on month/year ---
last_date = df['check_in'].max()
future_months = []
current_year = last_date.year
current_month = last_date.month

for i in range(1, 4):  # next 3 months
    month = current_month + i
    year = current_year
    if month > 12:
        month -= 12
        year += 1
    future_months.append((year, month))

# Generate all dates in these 3 months
forecast_dates = []
for year, month in future_months:
    # get number of days in month
    days_in_month = (pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)).day
    for day in range(1, days_in_month + 1):
        forecast_dates.append(datetime(year, month, day))

forecast_df = pd.DataFrame(forecast_dates, columns=['date'])
forecast_df['year'] = forecast_df['date'].dt.year
forecast_df['month'] = forecast_df['date'].dt.month
forecast_df['day'] = forecast_df['date'].dt.day
forecast_df['weekday'] = forecast_df['date'].dt.dayofweek

X_future = forecast_df[['year','month','day','weekday']]
forecast_df['predicted_bookings'] = model.predict(X_future).round().astype(int)

# Aggregate monthly forecast in chronological order
forecast_df['month_year'] = forecast_df['date'].dt.to_period('M')
forecast_monthly_ordered = (
    forecast_df.groupby('month_year')['predicted_bookings']
    .sum()
    .sort_index()
)

# Convert to 'Month Year' format for JSON keys
forecast_monthly = {d.strftime('%B %Y'): int(v) for d, v in forecast_monthly_ordered.items()}

# Save JSON in the same folder as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(script_dir, 'forecast_bookings.json')
with open(json_path, 'w') as f:
    json.dump({'forecast': forecast_monthly}, f, indent=4)

print(f"Forecast generated successfully. Saved to {json_path}")
