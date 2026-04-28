FROM mambaorg/micromamba:latest

WORKDIR /usr/local/lib/sepal-gee-bundle

USER root
RUN apt-get update && apt-get install -y \
    nano curl neovim supervisor netcat-openbsd net-tools git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

USER $MAMBA_USER
COPY --chown=$MAMBA_USER:$MAMBA_USER . /usr/local/lib/sepal-gee-bundle
RUN micromamba create -n sepal-gee-bundle python=3.12 pip -c conda-forge -y && \
    micromamba run -n sepal-gee-bundle pip install -e . --no-cache-dir && \
    micromamba clean --all --yes && \
    rm -rf ~/.cache/pip

EXPOSE 8765

USER root
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
