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
# libjemalloc2: allocator for the runtime (see ENV block near the end).
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor netcat-openbsd libjemalloc2 \
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
# sepal_environment.yml is the only place the environment is described -- it
# names the env, so `micromamba run -n sepal-gee-bundle` elsewhere is bound to
# it, and its pip section installs this project.
RUN micromamba create -y -f sepal_environment.yml && \
    micromamba clean --all --yes && \
    rm -rf ~/.cache/pip

# Run under jemalloc so freed per-session memory returns to the OS. glibc/pymalloc
# never release the arenas dented by per-session widget churn, so RSS ratchets to
# the peak working set and stays there until restart; jemalloc purges free pages
# on a decay timer, so memory follows users back down.
# NOTE: if the .so is missing, LD_PRELOAD is silently ignored and PYTHONMALLOC=malloc
# is worse than stock — after any image change verify jemalloc is actually loaded:
#   grep -c jemalloc /proc/<app-python-pid>/maps   # >= 1
# Placed after the build layers so image builds don't run under the preload.
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2 \
    PYTHONMALLOC=malloc \
    MALLOC_CONF=background_thread:true,dirty_decay_ms:1000,muzzy_decay_ms:1000

# asgi.py serves the archives, so the comm bridge must never also stand up: it
# gives every page an unauthenticated fetch to any 127.0.0.1 port, and this
# container is shared by many SEPAL users. Set ahead of the vectortileserver
# dependency itself -- inert until then, and easy to miss afterwards.
ENV VECTORTILESERVER_DISABLE_JUPYTER_LOOPBACK=1

EXPOSE 8768

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
