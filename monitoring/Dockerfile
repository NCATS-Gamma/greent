FROM python:3.8.0-alpine3.10

COPY ./ ./monitoring

ENV PYTHONPATH=/monitoring

WORKDIR ./monitoring

RUN apk update
RUN apk add postgresql-dev gcc musl-dev

RUN pip install neo4j pytest redis psycopg2-binary requests


