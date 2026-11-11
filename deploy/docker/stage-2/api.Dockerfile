FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY app/stage-2/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --requirement requirements.txt

COPY app/stage-2/api/main.py ./main.py

USER app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
