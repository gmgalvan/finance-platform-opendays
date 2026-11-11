FROM python:3.12-slim

# El CI pasa sha-<commit>; se ve en /health y en las trazas.
ARG APP_VERSION=dev

ENV APP_VERSION=${APP_VERSION} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY app/stage-2/market-data/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --requirement requirements.txt

COPY app/stage-2/market-data/market_data.py ./market_data.py

USER app

EXPOSE 8000

CMD ["uvicorn", "market_data:app", "--host", "0.0.0.0", "--port", "8000"]
