import pandas as pd
import mysql.connector
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ===============================
# 1️⃣ Connect to your MySQL (XAMPP)
# ===============================
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  # leave blank if no password in XAMPP
    database="hotel_system"
)
cursor = conn.cursor(dictionary=True)

# ===============================
# 2️⃣ Load user activity data
# ===============================
cursor.execute("""
    SELECT user_id, room_id, COUNT(*) AS interactions
    FROM user_activity
    WHERE room_id IS NOT NULL
    GROUP BY user_id, room_id
""")
data = cursor.fetchall()

df = pd.DataFrame(data)

if df.empty:
    print("⚠️ No user activity found!")
    exit()

# ===============================
# 3️⃣ Pivot the data to create a user–room interaction matrix
# ===============================
pivot = df.pivot_table(index='user_id', columns='room_id', values='interactions', fill_value=0)

# 🔹 Debug: Check the pivot table
print("=== User–Room Pivot Table ===")
print(pivot)
print("\n")

# ===============================
# 4️⃣ Compute user similarity
# ===============================
similarity = cosine_similarity(pivot)
similarity_df = pd.DataFrame(similarity, index=pivot.index, columns=pivot.index)

# 🔹 Debug: Check similarity matrix
print("=== User Similarity Matrix ===")
print(similarity_df)
print("\n")

# ===============================
# 5️⃣ Predict top rooms per user
# ===============================
predictions = []

for user_id in pivot.index:
    # Get similar users
    similar_users = similarity_df[user_id].sort_values(ascending=False)
    similar_users = similar_users[similar_users.index != user_id]  # exclude self
    
    # Weighted room scores
    weighted_scores = np.zeros(pivot.shape[1])
    if similar_users.sum() > 0:
        for sim_user, sim_score in similar_users.items():
            weighted_scores += sim_score * pivot.loc[sim_user].values
        # Normalize
        weighted_scores = weighted_scores / (similar_users.sum() + 1e-8)
    else:
        # No similar users, fallback to user's own activity
        weighted_scores = pivot.loc[user_id].values + 0.01  # small constant to avoid zero

    # Get top 5 rooms
    top_indices = np.argsort(weighted_scores)[::-1][:5]
    for idx in top_indices:
        room_id = pivot.columns[idx]
        score = weighted_scores[idx]
        predictions.append((user_id, int(room_id), float(score)))

# ===============================
# 6️⃣ Save predictions to ml_predictions
# ===============================
cursor.execute("DELETE FROM ml_predictions")  # Clear old data

insert_query = """
    INSERT INTO ml_predictions (user_id, room_id, predicted_score)
    VALUES (%s, %s, %s)
"""
cursor.executemany(insert_query, predictions)
conn.commit()

print(f"✅ ML predictions updated successfully! ({len(predictions)} entries inserted)")
from sklearn.cluster import KMeans

# ===============================
# 7️⃣ User Segmentation (K-Means)
# ===============================

# Fetch user activity with room prices
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="hotel_system"
)
cursor = conn.cursor(dictionary=True)

cursor.execute("""
    SELECT ua.user_id, r.price
    FROM user_activity ua
    JOIN rooms r ON ua.room_id = r.room_id
    WHERE ua.room_id IS NOT NULL
""")
data = cursor.fetchall()
df_price = pd.DataFrame(data)

# Compute average spend per user
user_features = df_price.groupby('user_id')['price'].mean().reset_index()
user_features.rename(columns={'price': 'avg_spend'}, inplace=True)

# K-Means clustering
kmeans = KMeans(n_clusters=2, random_state=42)
user_features['cluster'] = kmeans.fit_predict(user_features[['avg_spend']])

# Determine which cluster is Budget vs Premium
cluster_means = user_features.groupby('cluster')['avg_spend'].mean()
budget_cluster = cluster_means.idxmin()
user_features['cluster_label'] = user_features['cluster'].apply(
    lambda x: 'Budget' if x == budget_cluster else 'Premium'
)

# Save clusters to database
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_clusters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    cluster_label VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()  # <- make sure this is added
cursor.execute("DELETE FROM user_clusters")  # clear old data

records = [(row['user_id'], row['cluster_label']) for _, row in user_features.iterrows()]
cursor.executemany("INSERT INTO user_clusters (user_id, cluster_label) VALUES (%s, %s)", records)
conn.commit()

print("✅ User segmentation done (Budget / Premium clusters)")

cursor.close()
conn.close()

