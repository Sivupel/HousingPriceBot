import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


TOKEN = "YOUR_TELEGRAM_TOKEN"
API_URL = "http://127.0.0.1:8000/predict"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет.\n"
        "Отправь 6 чисел через запятую:\n"
        "area_total, area_living, area_kitchen, rooms_count, "
        "floor_number, floors_total\n\n"
        "Пример:\n"
        "45, 30, 8, 2, 5, 9"
    )


async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        values = [x.strip() for x in update.message.text.split(",")]

        if len(values) != 6:
            await update.message.reply_text(
                "Нужно ввести ровно 6 значений через запятую.\n"
                "Пример: 45, 30, 8, 2, 5, 9"
            )
            return

        data = {
            "area_total": float(values[0]),
            "area_living": float(values[1]),
            "area_kitchen": float(values[2]),
            "rooms_count": int(values[3]),
            "floor_number": int(values[4]),
            "floors_total": int(values[5]),
        }

    except ValueError as e:
        await update.message.reply_text(
            f"Ошибка ввода: {e}\n"
            "Пример: 45, 30, 8, 2, 5, 9"
        )
        return

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(API_URL, json=data)

        if response.status_code != 200:
            await update.message.reply_text(
                f"Ошибка API: {response.status_code}\n{response.text}"
            )
            return

        result = response.json()

        predicted_price = result["predicted_price"]
        similar_ad = result["similar_ad"]

        text = (
            f"Предсказанная цена: {predicted_price:.2f}\n\n"
            f"Похожее объявление:\n"
            f"offer_id: {similar_ad['offer_id']}\n"
            f"price: {similar_ad['price']:.2f}\n"
            f"distance: {similar_ad['distance']:.4f}"
        )

        await update.message.reply_text(text)

    except Exception as e:
        await update.message.reply_text(f"Ошибка при обращении к API:\n{e}")


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, predict)
    )

    application.run_polling()


if __name__ == "__main__":
    main()