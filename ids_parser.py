import logging
import os
import random
import re
import time
from typing import List, Optional

import requests
from dotenv import load_dotenv
from psycopg2 import extras, pool

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


class DataHunterScout:
    def __init__(self):
        self._load_config()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._init_db_pool()
        self._init_db_schema()

    def _load_config(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.cian.ru/",
        }
        self.db_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "database": os.getenv("DB_NAME", "house_pricing"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASS"),
            "port": os.getenv("DB_PORT", "5432"),
        }

    def _init_db_pool(self):
        try:
            self.db_pool = pool.SimpleConnectionPool(1, 20, **self.db_params)
            logging.info("Connection pool ready.")
        except Exception as e:
            logging.error(f"DB Pool failed: {e}")
            exit(1)

    def _init_db_schema(self):
        query = """
        CREATE TABLE IF NOT EXISTS queue (
            offer_id BIGINT PRIMARY KEY,
            region_id INTEGER,
            district_id INTEGER,
            status INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status);
        """
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                conn.commit()
        finally:
            self.db_pool.putconn(conn)

    def _upsert_ids(self, ids: List[str], region: int, district: Optional[int]) -> int:
        if not ids:
            return 0

        data = [(int(oid), region, district) for oid in ids]
        query = """
            INSERT INTO queue (offer_id, region_id, district_id)
            VALUES %s
            ON CONFLICT (offer_id) DO NOTHING
            RETURNING offer_id;
        """

        conn = self.db_pool.getconn()
        new_count = 0
        try:
            with conn.cursor() as cur:
                inserted = extras.execute_values(cur, query, data, fetch=True)
                conn.commit()
                new_count = len(inserted) if inserted else 0
        except Exception as e:
            logging.error(f"DB insert error: {e}")
            conn.rollback()
        finally:
            self.db_pool.putconn(conn)
        return new_count

    def scout_region(self, region: int, district: Optional[int] = None):
        logging.info(f"--- Scouting Region {region} ---")

        price_start = 10_000_000 if region == 1 else 1_500_000
        price_end = 150_000_000 if region == 1 else 40_000_000
        step = 1_000_000

        for p_min in range(price_start, price_end, step):
            p_max = p_min + step - 1
            logging.info(f"Price Window: {p_min:,} - {p_max:,} руб.")

            last_page_ids = set()
            consecutive_duplicates = 0

            for page in range(1, 55):
                url = f"https://www.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&region={region}&p={page}&minprice={p_min}&maxprice={p_max}"
                if district:
                    url += f"&district={district}"

                try:
                    time.sleep(random.uniform(3.5, 6.5))
                    res = self.session.get(url, timeout=20)

                    if res.status_code == 429:
                        logging.error("CAPTCHA! Sleeping 2 mins.")
                        time.sleep(120)
                        break

                    if res.status_code != 200:
                        logging.warning(f"HTTP {res.status_code} on page {page}.")
                        break

                    # Жесткий Regex: ищем ID только внутри ссылок (href)
                    found_ids = re.findall(
                        r'<a[^>]+href=["\'][^"\']*/sale/flat/(\d+)/?[^"\']*["\']',
                        res.text,
                    )
                    unique_ids = set(found_ids)

                    if not unique_ids or unique_ids == last_page_ids:
                        logging.info("End of listings for this window.")
                        break

                    newly_added = self._upsert_ids(list(unique_ids), region, district)
                    logging.info(
                        f"Page {page}: Found {len(unique_ids)} -> Added: {newly_added}"
                    )

                    # Модифицированный Smart Exit
                    if newly_added == 0 and len(unique_ids) > 0:
                        consecutive_duplicates += 1
                        if consecutive_duplicates >= 2:
                            logging.info(
                                "Two pages of duplicates. Moving to next window."
                            )
                            break
                    else:
                        consecutive_duplicates = 0

                    last_page_ids = unique_ids

                except Exception as e:
                    logging.error(f"Page {page} error: {e}")
                    break

    def get_final_stats(self):
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT region_id, COUNT(*) FROM queue GROUP BY region_id ORDER BY 1"
                )
                rows = cur.fetchall()
                print("\n" + "=" * 40)
                for rid, count in rows:
                    print(f"Region {rid:<5} | {count:<10} objects")

                cur.execute("SELECT COUNT(*) FROM queue")
                print("-" * 40)
                print(f"TOTAL DB SIZE: {cur.fetchone()[0]}")
                print("=" * 40 + "\n")
        finally:
            self.db_pool.putconn(conn)

    def shutdown(self):
        if hasattr(self, "db_pool") and self.db_pool:
            self.db_pool.closeall()
            logging.info("Pool closed.")


if __name__ == "__main__":
    # Для теста оставим только проблемные регионы
    TARGET_REGIONS = [16, 66, 23, 54]

    hunter = DataHunterScout()

    try:
        for rid in TARGET_REGIONS:
            try:
                hunter.scout_region(rid)
            except Exception as e:
                logging.critical(f"Critical error in region {rid}: {e}")
                continue
    except KeyboardInterrupt:
        logging.info("Stopped by user.")
    finally:
        hunter.get_final_stats()
        hunter.shutdown()
