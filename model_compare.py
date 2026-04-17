import pandas as pd
import joblib

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split


df = pd.read_csv("for_ml_sample_202604170834.csv")
df = df.fillna(df.median(numeric_only=True))

X = df[
    [
        "area_total",
        "area_living",
        "area_kitchen",
        "rooms_count",
        "floor_number",
        "floors_total"
    ]
]

y = df["price"]

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

models = {
    "LinearRegression": LinearRegression(),
    "RandomForest": RandomForestRegressor(
        n_estimators=100,
        max_depth=5,
        random_state=42
    ),
    "GradientBoosting": GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=3,
        random_state=42
    )
}

best_model_name = None
best_model = None
best_mae = float("inf")

for name, model in models.items():
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)

    print(f"{name}: MAE = {mae:.2f}")

    if mae < best_mae:
        best_mae = mae
        best_model_name = name
        best_model = model

print()
print(f"Лучшая модель: {best_model_name}")
print(f"Лучший MAE: {best_mae:.2f}")

joblib.dump(best_model, "best_model.pkl")

print("\nМодель сохранена в best_model.pkl")