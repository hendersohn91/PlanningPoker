FROM python:3.13-alpine

ARG http_proxy
ARG https_proxy

WORKDIR /usr/src/app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "api.py"]
