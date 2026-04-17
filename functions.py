import joblib
import pandas as pd
from sklearn.neighbors import NearestNeighbors


FEATURES = [
    "area_total",
    "area_living",
    "area_kitchen",
    "rooms_count",
    "floor_number",
    "floors_total"
]


def load_data(filename: str) -> pd.DataFrame:
    df = pd.read_csv(filename)
    df = df.fillna(df.median(numeric_only=True))
    return df


def load_price_model(filename: str):
    return joblib.load(filename)


def build_neighbors_model(df: pd.DataFrame) -> NearestNeighbors:
    x = df[FEATURES]
    model = NearestNeighbors(n_neighbors=1)
    model.fit(x)
    return model


def get_user_input() -> pd.DataFrame:
    area_total = float(input("Введите общую площадь: "))
    area_living = float(input("Введите жилую площадь: "))
    area_kitchen = float(input("Введите площадь кухни: "))
    rooms_count = int(input("Введите количество комнат: "))
    floor_number = int(input("Введите этаж: "))
    floors_total = int(input("Введите этажность дома: "))

    new_object = pd.DataFrame(
        [
            {
                "area_total": area_total,
                "area_living": area_living,
                "area_kitchen": area_kitchen,
                "rooms_count": rooms_count,
                "floor_number": floor_number,
                "floors_total": floors_total
            }
        ]
    )
    return new_object


def predict_price(model, new_object: pd.DataFrame) -> float:
    return model.predict(new_object)[0]


def find_similar_ad(
    df: pd.DataFrame,
    neighbors_model: NearestNeighbors,
    new_object: pd.DataFrame
) -> tuple[pd.Series, float]:
    distances, indices = neighbors_model.kneighbors(new_object)
    nearest_index = indices[0][0]
    nearest_row = df.iloc[nearest_index]
    distance = distances[0][0]
    return nearest_row, distance


def main() -> None:
    df = load_data("for_ml_sample_202604170834.csv")
    price_model = load_price_model("best_model.pkl")
    neighbors_model = build_neighbors_model(df)

    new_object = get_user_input()

    predicted_price = predict_price(price_model, new_object)
    nearest_row, distance = find_similar_ad(df, neighbors_model, new_object)

    print()
    print(f"Предсказанная цена: {predicted_price:.2f}")
    print("Самое похожее объявление:")
    print(f"offer_id: {nearest_row['offer_id']}")
    print(f"price: {nearest_row['price']}")
    print(f"distance: {distance:.4f}")


if __name__ == "__main__":
    main()