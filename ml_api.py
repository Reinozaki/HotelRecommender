from flask import Flask, request, jsonify
import joblib
import mysql.connector

app = Flask(__name__)
model = joblib.load("recommender_model.pkl")

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="hotel_system"
)
cursor = db.cursor(dictionary=True)

@app.route("/recommend", methods=["GET"])
def recommend():
    user_id = int(request.args.get("user_id"))

    # Get all available rooms
    cursor.execute("SELECT room_id, room_name, price FROM rooms WHERE status='Available'")
    rooms = cursor.fetchall()

    # Predict score for each room
    recommendations = []
    for room in rooms:
        pred = model.predict(user_id, room["room_id"]).est
        recommendations.append({
            "room_id": room["room_id"],
            "room_name": room["room_name"],
            "price": room["price"],
            "score": pred
        })

    # Sort by predicted score
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    
    return jsonify(recommendations[:5])  # return top 5

if __name__ == "__main__":
    app.run(port=5000, debug=True)
