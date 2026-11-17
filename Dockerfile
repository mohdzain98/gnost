FROM python:3.12-slim
ARG GNOST_VERSION
# Extra pip flags, e.g. --extra-index-url for release candidates.
ARG PIP_EXTRA=""
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir ${PIP_EXTRA} "gnost==${GNOST_VERSION}" \
    && git config --system --add safe.directory /repo
WORKDIR /repo
ENTRYPOINT ["gnost"]
