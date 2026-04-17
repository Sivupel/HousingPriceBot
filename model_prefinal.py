import joblib
import pandas as pd
from sklearn.neighbors import NearestNeighbors


df = pd.read_csv("for_ml_sample_202604170834.csv")
df = df.fillna(df.median(numeric_only=True))

features = [
    "area_total",
    "area_living",
    "area_kitchen",
    "rooms_count",
    "floor_number",
    "floors_total"
]

X = df[features]

price_model = joblib.load("best_model.pkl")

neighbors_model = NearestNeighbors(n_neighbors=1)
neighbors_model.fit(X)

new_object = pd.DataFrame(
    [
        {
            "area_total": 45.0,
            "area_living": 30.0,
            "area_kitchen": 8.0,
            "rooms_count": 2,
            "floor_number": 5,
            "floors_total": 9
        }
    ]
)

predicted_price = price_model.predict(new_object)[0]

distances, indices = neighbors_model.kneighbors(new_object)

nearest_index = indices[0][0]
nearest_row = df.iloc[nearest_index]

print(f"Предсказанная цена: {predicted_price:.2f}")
print()
print("Самое похожее объявление:")
print(f"offer_id: {nearest_row['offer_id']}")
print(f"price: {nearest_row['price']}")
print(f"distance: {distances[0][0]:.4f}")