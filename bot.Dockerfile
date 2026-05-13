FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
ENV API_URL=http://api:8000/predict
CMD ["python", "bot.py"]