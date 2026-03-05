import json
import logging
import os
import random
import time

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Пул реальных User-Agent для ротации и имитации живых пользователей
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "house_pricing"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "postgres"),
        port=os.getenv("DB_PORT", "5432"),
    )


def extract_features_advanced(html_text, offer_id):
    """Парсинг скрытого JSON-состояния страницы с дампом ошибок."""
    start_marker = "window._cianConfig['frontend-offer-card'] ="
    start_pos = html_text.find(start_marker)

    # Если маркера нет, мы поймали капчу или заглушку. Сохраняем улики.
    if start_pos == -1:
        with open(f"error_{offer_id}.html", "w", encoding="utf-8") as f:
            f.write(html_text)
        return None

    json_start = html_text.find("[{", start_pos)
    if json_start == -1:
        return None

    brackets = 0
    json_end = -1
    for i in range(json_start, len(html_text)):
        if html_text[i] == "[":
            brackets += 1
        elif html_text[i] == "]":
            brackets -= 1
            if brackets == 0:
                json_end = i + 1
                break

    if json_end == -1:
        return None

    try:
        full_list = json.loads(html_text[json_start:json_end])
        state = next(
            (
                item.get("value", {})
                for item in full_list
                if isinstance(item, dict) and item.get("key") == "defaultState"
            ),
            None,
        )
        if not state:
            return None

        offer = state.get("offerData", {}).get("offer", {})
        bld = offer.get("building", {})
        nearest_metro = offer.get("geo", {}).get("undergrounds", [{}])

        return {
            "offer_id": offer_id,
            "url": f"https://www.cian.ru/sale/flat/{offer_id}/",
            "price": offer.get("bargainTerms", {}).get("price"),
            "area_total": offer.get("totalArea"),
            "area_living": offer.get("livingArea"),
            "area_kitchen": offer.get("kitchenArea"),
            "rooms_count": offer.get("roomsCount"),
            "floor_number": offer.get("floorNumber"),
            "floors_total": bld.get("floorsCount"),
            "house_material": bld.get("houseMaterialType"),
            "build_year": bld.get("buildYear"),
            "ceiling_height": bld.get("ceilingHeight"),
            "lifts_pass": bld.get("passengerLiftsCount", 0),
            "lifts_cargo": bld.get("cargoLiftsCount", 0),
            "parking_type": bld.get("parking", {}).get("type"),
            "repair_type": offer.get("repairType"),
            "is_apartment": offer.get("isApartments", False),
            "balconies_count": offer.get("balconiesCount", 0),
            "loggias_count": offer.get("loggiasCount", 0),
            "metro_min": nearest_metro[0].get("travelTime") if nearest_metro else None,
            "lat": offer.get("geo", {}).get("coordinates", {}).get("lat"),
            "lng": offer.get("geo", {}).get("coordinates", {}).get("lng"),
            "raw_json": json.dumps(offer, ensure_ascii=False),
        }
    except Exception as e:
        logging.error(f"JSON Parse Error для ID {offer_id}: {e}")
        with open(f"error_json_{offer_id}.html", "w", encoding="utf-8") as f:
            f.write(html_text)
        return None


def run_stealth_worker():
    conn = get_db_connection()
    session = requests.Session()
    logging.info("Stealth Worker запущен. Ожидание задач...")

    while True:
        try:
            with conn.cursor() as cur:
                # Случайная выборка для репрезентативности датасета
                cur.execute("""
                    SELECT offer_id FROM queue 
                    WHERE status = 0 
                    ORDER BY RANDOM()
                    LIMIT 1 
                    FOR UPDATE SKIP LOCKED;
                """)
                row = cur.fetchone()

                if not row:
                    logging.info("Очередь пуста или заблокирована. Сон 60 сек...")
                    conn.commit()
                    time.sleep(60)
                    continue

                oid = row[0]
                url = f"https://www.cian.ru/sale/flat/{oid}/"

                # Динамические заголовки
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept-Language": "ru-RU,ru;q=0.9",
                    "Referer": "https://www.cian.ru/",
                }

                res = session.get(url, headers=headers, timeout=15)

                if res.status_code in [403, 429]:
                    logging.error(
                        f"HTTP {res.status_code} (Бан). Уходим в глубокий сон на 15 минут..."
                    )
                    conn.rollback()  # ID возвращается в очередь
                    time.sleep(900)
                    continue

                elif res.status_code == 404:
                    cur.execute(
                        "UPDATE queue SET status = 2 WHERE offer_id = %s", (oid,)
                    )
                    logging.warning(f"ID {oid} удален с сайта (404).")

                elif res.status_code == 200:
                    data = extract_features_advanced(res.text, oid)
                    if data:
                        cols = list(data.keys())
                        query = f"""
                            INSERT INTO for_ML ({", ".join(cols)}) 
                            VALUES ({", ".join(["%(" + c + ")s" for c in cols])})
                            ON CONFLICT (offer_id) DO UPDATE SET 
                                price = EXCLUDED.price,
                                parsed_at = CURRENT_TIMESTAMP;
                        """
                        cur.execute(query, data)
                        cur.execute(
                            "UPDATE queue SET status = 1 WHERE offer_id = %s", (oid,)
                        )
                        logging.info(f"Успех: ID {oid} сохранен в for_ML.")
                    else:
                        cur.execute(
                            "UPDATE queue SET status = 3 WHERE offer_id = %s", (oid,)
                        )
                        logging.error(f"Пустой JSON для ID {oid} (Сохранен дамп HTML)")
                else:
                    cur.execute(
                        "UPDATE queue SET status = 4 WHERE offer_id = %s", (oid,)
                    )
                    logging.error(f"HTTP {res.status_code} для ID {oid}")

                conn.commit()

        except psycopg2.IntegrityError as e:
            conn.rollback()
            logging.error(f"Сработал CHECK БД для ID {oid}. Ошибка: {e}")
            with conn.cursor() as cur:
                cur.execute("UPDATE queue SET status = 5 WHERE offer_id = %s", (oid,))
                conn.commit()

        except Exception as e:
            conn.rollback()
            logging.critical(f"Критическая ошибка: {e}")
            time.sleep(10)

        # Анти-фрод пауза (в среднем 7 секунд)
        time.sleep(random.uniform(5.0, 9.0))


if __name__ == "__main__":
    run_stealth_worker()
