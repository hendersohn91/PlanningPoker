FROM python:3.10.1-alpine AS builder

ARG http_proxy
ARG https_proxy

WORKDIR /usr/src/app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

FROM busybox:latest
COPY --from=builder /usr/local/lib/python3.10/site-packages/ /pip-packages/

