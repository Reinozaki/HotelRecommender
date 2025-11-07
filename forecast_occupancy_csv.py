import mysql.connector
import json
from datetime import datetime
import calendar
import os
import csv

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
    print("⚠️ forecast_bookings.json not found. Will generate synthetic data.")

# -----------------------------
# Fallback / synthetic data for testing (next 3 months only)
# -----------------------------
if not predicted:
    today = datetime.today()
    predicted = {}
    for i in range(1, 4):  # next 3 months
        month = today.month + i
        year = today.year
        if month > 12:
            month -= 12
            year += 1
        month_label = f"{calendar.month_name[month]} {year}"
        # Generate synthetic bookings between 50% and 100% of total rooms
        bookings = max(1, round(total_rooms * (0.5 + 0.5 * i / 3)))
        predicted[month_label] = bookings
    print("✅ Generated synthetic predicted bookings for 3 months.")

conn.close()

# -----------------------------
# Compute occupancy rate (%)
# -----------------------------
forecast_list = []
for month_label, bookings in predicted.items():
    occupancy = min(round((bookings / total_rooms) * 100, 2), 100)
    forecast_list.append({
        "Month": month_label,
        "Predicted Bookings": bookings,
        "Total Rooms": total_rooms,
        "Occupancy (%)": occupancy
    })

# -----------------------------
# Save to CSV
# -----------------------------
csv_file = os.path.join(script_dir, "forecast_occupancy.csv")
with open(csv_file, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["Month", "Predicted Bookings", "Total Rooms", "Occupancy (%)"])
    writer.writeheader()
    for row in forecast_list:
        writer.writerow(row)

print("\n✅ Forecast CSV generated:")
for row in forecast_list:
    print(f"   • {row['Month']}: {row['Predicted Bookings']} bookings, Occupancy {row['Occupancy (%)']}%")

print(f"\n💾 Saved CSV to {csv_file}")
