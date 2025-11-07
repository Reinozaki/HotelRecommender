import pandas as pd
import mysql.connector
from surprise import Dataset, Reader, SVD
from surprise.model_selection import train_test_split
import joblib

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="hotel_system"
)
cursor = db.cursor(dictionary=True)

# Fetch user history
cursor.execute("SELECT user_id, room_id, rating FROM user_history")
rows = cursor.fetchall()

df = pd.DataFrame(rows)

# Define rating scale
reader = Reader(rating_scale=(1, 5))
data = Dataset.load_from_df(df[['user_id', 'room_id', 'rating']], reader)

# Train-test split
trainset, testset = train_test_split(data, test_size=0.2)

# Train SVD recommender
algo = SVD()
algo.fit(trainset)

# Save trained model
joblib.dump(algo, "recommender_model.pkl")
print("✅ Model trained and saved as recommender_model.pkl")
