# Creates a dockerfile with pre-commit preconfigured.
# Can be used to reduce time for linting stage.

FROM python:3.10-slim-buster

ENV PRE_COMMIT_VERSION 3.0.4

RUN apt-get update \
  && apt-get install -y --no-install-recommends git \
  && apt-get purge -y --auto-remove \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir /tmp/pre-commit && mkdir /project && cd /tmp/pre-commit \
  && git init . \
  && python3 -m pip install --no-cache-dir --upgrade pip

RUN cd /tmp/pre-commit \
  && python3 -m pip install --no-cache-dir pre-commit==${PRE_COMMIT_VERSION}

ARG src=".pre-commit-config.yaml"
COPY ${src} /tmp/pre-commit/.pre-commit-config.yaml
RUN cd /tmp/pre-commit \
  && pre-commit install \
  && pre-commit run
