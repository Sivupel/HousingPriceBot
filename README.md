# HousingPriceBot

Сервис для предсказания стоимости недвижимости и поиска наиболее похожего объявления на основе параметров объекта.

Проект включает:
- модель машинного обучения
- REST API на FastAPI
- Telegram-бот для взаимодействия с пользователем


## Описание

Система принимает параметры недвижимости (площадь, комнаты, этаж и т.д.), предсказывает стоимость объекта и находит наиболее близкое объявление из датасета.


## Используемые технологии

- python
- pandas
- scikit-learn
- joblib
- FastAPI
- uvicorn
- python-telegram-bot
- httpx


## Данные

Используются следующие признаки:

- area_total — общая площадь
- area_living — жилая площадь
- area_kitchen — площадь кухни
- rooms_count — количество комнат
- floor_number — этаж
- floors_total — этажность дома

Целевая переменная:

- price — стоимость недвижимости


## Модели

В проекте сравниваются следующие модели:

- LinearRegression
- RandomForestRegressor
- GradientBoostingRegressor

Лучшая модель выбирается по метрике MAE (Mean Absolute Error).


## Установка зависимостей

pip install -r requirements.txt


Для запуска сервера используется uvicorn:
uvicorn api:app --reload


## Запуск Telegram-бота

Перед запуском необходимо создать бота через BotFather в Telegram и получить токен.

В файле bot.py укажи токен:

TOKEN = "your_telegram_bot_token"

После этого запустите бот:
python bot.py
