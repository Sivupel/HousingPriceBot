install:
	pip install -r requirements.txt

train:
	python model_compare.py

run-api:
	uvicorn api:app --reload

run-bot:
	python bot.py

check:
	python appraiser.py

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.pyc

help:
	@echo "make install  - установить зависимости"
	@echo "make train    - обучить и сохранить модель"
	@echo "make run-api  - запустить FastAPI через uvicorn"
	@echo "make run-bot  - запустить Telegram-бота"
	@echo "make check    - проверить работу предсказания"
	@echo "make clean    - очистить временные файлы"