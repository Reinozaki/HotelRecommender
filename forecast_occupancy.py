import mysql.connector
import json
from datetime import datetime
import calendar
import os

# -----------------------------
# Connect to Database
# -----------------------------
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="hotel_system"
    )
    cursor = conn.cursor(dictionary=True)
    print("✅ Connected to hotel_system database.")
except mysql.connector.Error as err:
    print(f"❌ Database connection failed: {err}")
    exit(1)

# -----------------------------
# Get total number of rooms
# -----------------------------
cursor.execute("SELECT COUNT(*) AS total_rooms FROM rooms")
total_rooms = cursor.fetchone()['total_rooms']
if total_rooms == 0:
    print("⚠️ No rooms found in the database. Cannot compute occupancy.")
    conn.close()
    exit(0)

# -----------------------------
# Load predicted bookings
# -----------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
predict_file = os.path.join(script_dir, "forecast_bookings.json")

if os.path.exists(predict_file):
    with open(predict_file, "r") as f:
        data = json.load(f)
    predicted = data.get('forecast', {})
    print("✅ Loaded predicted bookings from JSON.")
else:
    predicted = {}
    print("⚠️ forecast_bookings.json not found. Using fallback to historical data.")

# -----------------------------
# Fallback: Compute last 3 months average if JSON missing
# -----------------------------
if not predicted:
    cursor.execute("""
        SELECT DATE_FORMAT(check_in, '%Y-%m') AS month_label, COUNT(*) AS total
        FROM reservations
        GROUP BY month_label
        ORDER BY month_label DESC
        LIMIT 3
    """)
    rows = cursor.fetchall()
    for r in rows:
        predicted[r['month_label']] = r['total']
    print("✅ Computed fallback predicted bookings from last 3 months reservations.")

conn.close()

# -----------------------------
# Compute occupancy rate (%)
# -----------------------------
forecast = {}
for month_label, bookings in predicted.items():
    occupancy = min(round((bookings / total_rooms) * 100, 2), 100)
    forecast[month_label] = occupancy

# Ensure chronological order
def parse_month_label(label):
    try:
        # handle 'Month Year' format
        return datetime.strptime(label, "%B %Y")
    except ValueError:
        # fallback for 'YYYY-MM' or unknown format
        try:
            return datetime.strptime(label, "%Y-%m")
        except:
            return datetime.now()

forecast_ordered = dict(sorted(forecast.items(), key=lambda x: parse_month_label(x[0])))

# -----------------------------
# Save results to JSON
# -----------------------------
forecast_data = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "forecast": forecast_ordered
}

file_path = os.path.join(script_dir, "forecast.json")
with open(file_path, "w") as f:
    json.dump(forecast_data, f, indent=2)

print("\n✅ Forecasted Occupancy for the Next 3 Months:")
for month, rate in forecast_ordered.items():
    print(f"   • {month}: {rate}%")

print(f"\n💾 Saved forecast results to {file_path}")
