FROM runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404

ARG FORGE_REVISION
LABEL org.opencontainers.image.source="https://github.com/joonghui0926/FORGE"
LABEL org.opencontainers.image.revision=$FORGE_REVISION

WORKDIR /opt/forge
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
COPY workers ./workers
RUN python -m pip install --no-cache-dir .[cloud,gpu,data]

ENV PYTHONUNBUFFERED=1 \
    FORGE_ENV=production \
    PYTHONPATH=/opt/forge/src

CMD ["python", "-m", "workers.runpod_entrypoint"]
