FROM python:3.11.9-slim-bookworm

RUN apt-get update \
    && apt-get install --yes --no-install-recommends build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/certigap
COPY . .

RUN python -m pip install --no-cache-dir .
RUN python build_cpp_core.py

CMD ["certigap", "reproduce", "--mode", "tests"]
