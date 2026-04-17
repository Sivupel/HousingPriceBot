import joblib
import pandas as pd
from fastapi import FastAPI
from sklearn.neighbors import NearestNeighbors


app = FastAPI()

FEATURES = [
    "area_total",
    "area_living",
    "area_kitchen",
    "rooms_count",
    "floor_number",
    "floors_total"
]

# загрузка при старте
df = pd.read_csv("for_ml_sample_202604170834.csv")
df = df.fillna(df.median(numeric_only=True))

price_model = joblib.load("best_model.pkl")

neighbors_model = NearestNeighbors(n_neighbors=1)
neighbors_model.fit(df[FEATURES])


@app.get("/")
def root():
    return {"message": "API работает"}


@app.post("/predict")
def predict(data: dict):
    new_object = pd.DataFrame([data])

    predicted_price = price_model.predict(new_object)[0]

    distances, indices = neighbors_model.kneighbors(new_object)
    nearest_row = df.iloc[indices[0][0]]

    return {
        "predicted_price": float(predicted_price),
        "similar_ad": {
            "offer_id": int(nearest_row["offer_id"]),
            "price": float(nearest_row["price"]),
            "distance": float(distances[0][0])
        }
    }