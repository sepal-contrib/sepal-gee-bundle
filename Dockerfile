FROM mambaorg/micromamba:latest

LABEL org.opencontainers.image.source="https://github.com/sepal-contrib/sepal-gee-bundle"

# Align the in-container mambauser uid/gid with the host user that bind-mounts
# files into the container (e.g. the Earth Engine credentials in dev). Override
# at build time with --build-arg HOST_UID=$(id -u) --build-arg HOST_GID=$(id -g)
# or via the HOST_UID/HOST_GID env vars consumed by docker-compose.
ARG HOST_UID=1000
ARG HOST_GID=1000

WORKDIR /usr/local/lib/sepal-gee-bundle

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/* \
    && groupmod -g ${HOST_GID} $MAMBA_USER \
    && usermod  -u ${HOST_UID} -g ${HOST_GID} $MAMBA_USER \
    && chown -R ${HOST_UID}:${HOST_GID} /home/$MAMBA_USER /opt/conda /usr/local/lib/sepal-gee-bundle

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

USER $MAMBA_USER
COPY --chown=$MAMBA_USER:$MAMBA_USER . /usr/local/lib/sepal-gee-bundle
RUN micromamba create -n sepal-gee-bundle python=3.12 pip -c conda-forge -y && \
    micromamba run -n sepal-gee-bundle pip install -e . --no-cache-dir && \
    micromamba clean --all --yes && \
    rm -rf ~/.cache/pip

EXPOSE 8768

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
