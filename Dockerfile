FROM python:3.12-slim
ARG GNOST_VERSION
# Extra pip flags, e.g. --extra-index-url for release candidates.
ARG PIP_EXTRA=""
# The package index can lag a few minutes behind a fresh release (one mirror lists the
# version, another not yet), so the install is retried before the build gives up.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && for try in 1 2 3 4 5 6; do \
         pip install --no-cache-dir ${PIP_EXTRA} "gnost==${GNOST_VERSION}" && break; \
         [ "$try" = 6 ] && exit 1; \
         echo "gnost==${GNOST_VERSION} not installable yet (try $try of 6); waiting 20s"; \
         sleep 20; \
       done \
    && git config --system --add safe.directory /repo
WORKDIR /repo
ENTRYPOINT ["gnost"]
