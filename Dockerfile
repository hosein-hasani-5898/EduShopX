FROM python:3.11.4-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip

COPY req.txt .
RUN pip install --no-cache-dir -r req.txt

COPY . .

