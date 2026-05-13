import os
import httpx
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ---------- Конфигурация из переменных окружения ----------
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/predict")

# ---------- Состояния для пошагового ввода ----------
(
    AREA_TOTAL,
    AREA_LIVING,
    AREA_KITCHEN,
    ROOMS,
    FLOOR,
    FLOORS_TOTAL,
) = range(6)

# Состояние для быстрого ввода
QUICK_INPUT = 10

# ---------- Вспомогательные данные ----------
FEATURE_NAMES = [
    "общую площадь (area_total)",
    "жилую площадь (area_living)",
    "площадь кухни (area_kitchen)",
    "количество комнат",
    "этаж",
    "этажность дома",
]

# ---------- Главное меню ----------
main_keyboard = ReplyKeyboardMarkup(
    [
        ["📊 Рассчитать стоимость"],
        ["⚡ Быстрый ввод (6 чисел)", "📘 Помощь"],
    ],
    resize_keyboard=True,
)

# ---------- Функция вызова API ----------
async def fetch_prediction(data: dict) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(API_URL, json=data)
    resp.raise_for_status()
    return resp.json()

# ---------- Форматирование ответа ----------
def format_result(result: dict) -> str:
    predicted = result["predicted_price"]
    similar = result["similar_ad"]
    return (
        f"✅ <b>Предсказанная цена:</b> {predicted:,.2f} руб.\n\n"
        f"🔍 <b>Похожее объявление:</b>\n"
        f"ID: {similar['offer_id']}\n"
        f"Цена: {similar['price']:,.2f} руб.\n"
        f"Расстояние: {similar['distance']:.4f}"
    )

# ---------- Стартовые команды ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🏠 <b>HousingPriceBot</b>\n"
        "Я предсказываю стоимость недвижимости и нахожу похожие объявления.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=main_keyboard,
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📘 <b>Как использовать бота</b>\n\n"
        "<b>Пошаговый расчёт</b> – бот по очереди запросит 6 параметров.\n"
        "<b>Быстрый ввод</b> – отправьте 6 чисел через запятую.\n"
        "Пример: <code>45, 30, 8, 2, 5, 9</code>\n\n"
        "При быстром вводе параметры находятся в следующем порядке: "
        "общая площадь, жилая площадь, площадь кухни, "
        "комнаты, этаж, этажность дома.",
        parse_mode="HTML",
        reply_markup=main_keyboard,
    )

# ---------- Универсальная отмена ----------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "❌ Ввод отменён.",
        reply_markup=main_keyboard,
    )
    return ConversationHandler.END

# ---------- Диалог: пошаговый ввод (с защитой от кнопки "Отмена") ----------
async def step_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"📝 Шаг 1/6. Введите {FEATURE_NAMES[0]}:",
        reply_markup=ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True),
    )
    return AREA_TOTAL

async def step_area_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    try:
        context.user_data["area_total"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return AREA_TOTAL
    await update.message.reply_text(f"📝 Шаг 2/6. Введите {FEATURE_NAMES[1]}:")
    return AREA_LIVING

async def step_area_living(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    try:
        context.user_data["area_living"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return AREA_LIVING
    await update.message.reply_text(f"📝 Шаг 3/6. Введите {FEATURE_NAMES[2]}:")
    return AREA_KITCHEN

async def step_area_kitchen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    try:
        context.user_data["area_kitchen"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return AREA_KITCHEN
    await update.message.reply_text(f"📝 Шаг 4/6. Введите {FEATURE_NAMES[3]}:")
    return ROOMS

async def step_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    try:
        context.user_data["rooms_count"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите целое число.")
        return ROOMS
    await update.message.reply_text(f"📝 Шаг 5/6. Введите {FEATURE_NAMES[4]}:")
    return FLOOR

async def step_floor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    try:
        context.user_data["floor_number"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите целое число.")
        return FLOOR
    await update.message.reply_text(f"📝 Шаг 6/6. Введите {FEATURE_NAMES[5]}:")
    return FLOORS_TOTAL

async def step_floors_total(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)
    try:
        context.user_data["floors_total"] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите целое число.")
        return FLOORS_TOTAL

    data = {
        "area_total": context.user_data["area_total"],
        "area_living": context.user_data["area_living"],
        "area_kitchen": context.user_data["area_kitchen"],
        "rooms_count": context.user_data["rooms_count"],
        "floor_number": context.user_data["floor_number"],
        "floors_total": context.user_data["floors_total"],
    }

    await update.message.reply_text("⏳ Считаю...", reply_markup=ReplyKeyboardRemove())

    try:
        result = await fetch_prediction(data)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка при обращении к API: {e}",
            reply_markup=main_keyboard,
        )
        return ConversationHandler.END

    await update.message.reply_text(
        format_result(result),
        parse_mode="HTML",
        reply_markup=main_keyboard,
    )
    return ConversationHandler.END

# ---------- Диалог: быстрый ввод ----------
async def quick_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "⚡ Введите 6 чисел через запятую:\n"
        "Общая площадь, жилая площадь, площадь кухни, "
        "комнаты, этаж, этажность дома.\n\n"
        "Пример: <code>45, 30, 8, 2, 5, 9</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True),
    )
    return QUICK_INPUT

async def quick_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "❌ Отмена":
        return await cancel(update, context)

    text = update.message.text
    try:
        parts = [x.strip() for x in text.split(",")]
        if len(parts) != 6:
            raise ValueError("Должно быть 6 чисел")
        data = {
            "area_total": float(parts[0]),
            "area_living": float(parts[1]),
            "area_kitchen": float(parts[2]),
            "rooms_count": int(parts[3]),
            "floor_number": int(parts[4]),
            "floors_total": int(parts[5]),
        }
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Ошибка ввода: {e}\nПример: 45, 30, 8, 2, 5, 9"
        )
        return QUICK_INPUT

    await update.message.reply_text("⏳ Считаю...", reply_markup=ReplyKeyboardRemove())

    try:
        result = await fetch_prediction(data)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Ошибка API: {e}",
            reply_markup=main_keyboard,
        )
        return ConversationHandler.END

    await update.message.reply_text(
        format_result(result),
        parse_mode="HTML",
        reply_markup=main_keyboard,
    )
    return ConversationHandler.END

# ---------- Сборка приложения ----------
def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Диалог пошагового расчёта
    step_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📊 Рассчитать стоимость$"), step_start),
        ],
        states={
            AREA_TOTAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_area_total)],
            AREA_LIVING: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_area_living)],
            AREA_KITCHEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_area_kitchen)],
            ROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_rooms)],
            FLOOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_floor)],
            FLOORS_TOTAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, step_floors_total)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)],
    )

    # Диалог быстрого ввода
    quick_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^⚡ Быстрый ввод \\(6 чисел\\)$"), quick_start),
        ],
        states={
            QUICK_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, quick_process)],
        },
        fallbacks=[MessageHandler(filters.Regex("^❌ Отмена$"), cancel)],
    )

    # Команды и кнопки меню
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Regex("^📘 Помощь$"), help_command))

    # Диалоги
    application.add_handler(step_conv)
    application.add_handler(quick_conv)

    # Заглушка на случай непредусмотренных сообщений
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, start)
    )

    application.run_polling()

if __name__ == "__main__":
    main()