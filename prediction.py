import joblib
import pandas as pd


model = joblib.load("best_model.pkl")

new_data = pd.DataFrame(
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

prediction = model.predict(new_data)

print(f"Предсказанная цена: {prediction[0]:.2f}")