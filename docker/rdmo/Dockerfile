FROM debian:latest

ARG UID GID
# to install rdmo from a git fork/branch/tag/commit instead of the pinned pypi
# release below, pass e.g.
#   --build-arg RDMO_INSTALL_URL=git+https://github.com/<you>/rdmo.git@<branch>
# (see RDMO_INSTALL_URL in .env.defaults for the docker-compose equivalent)
ARG RDMO_INSTALL_URL=""
# rdmo's package.json pins an exact node "engines" range (e.g. 22.22.x) and its
# webpack.config.js hard-fails the build on any other version, so this needs to
# track whatever rdmo's package.json currently requires - bump it if that changes
ARG NODE_VERSION="22.22.3"
ENV USER=rdmo
ENV HOME="/home/rdmo"
ENV PATH="${PATH}:${HOME}/.local/bin:${HOME}/sh"
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt update -y && apt upgrade -y && apt install -y \
  python3 python3-dev python3-pip locales python-is-python3
RUN rm "$(find /usr/lib -type f -regex ".*python.*EXTERNALLY-MANAGED.*")"
#RUN ln -s /usr/bin/python3 /usr/bin/python
#RUN python -m pip install --upgrade pip

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
RUN dpkg-reconfigure --frontend=noninteractive locales
RUN update-locale LANG=en_US.UTF-8

RUN apt install -y curl git micro procps vim
RUN apt install -y pandoc texlive-xetex

# node/npm are only needed to build rdmo's frontend when installing from git (see below):
# the compiled JS/CSS bundles are gitignored in the rdmo repo and are normally only
# built and bundled into the wheel by rdmo's own release CI, so a plain
# `pip install git+...` gives you the backend but leaves the old frontend assets in place.
# installed from the official upstream tarball (rather than e.g. nodesource, which only
# tracks the latest patch of a major version) since webpack.config.js hard-fails the
# build unless the node version satisfies package.json's "engines" range exactly.
RUN if [ -n "${RDMO_INSTALL_URL}" ]; then \
      apt install -y xz-utils && \
      NODE_ARCH="$(dpkg --print-architecture | sed -e 's/amd64/x64/' -e 's/armhf/armv7l/')" && \
      curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" -o /tmp/node.tar.xz && \
      tar -xJf /tmp/node.tar.xz -C /usr/local --strip-components=1 && \
      rm /tmp/node.tar.xz ; \
    fi
RUN rm -rf /var/lib/apt/lists/*

COPY ./rootfs /
RUN chmod -R 777 /tmp

RUN groupadd -g "${GID}" "${USER}"
RUN useradd -m -u "${UID}" -g "${GID}" -s /bin/bash "${USER}"

RUN curl --output ${HOME}/.bashrc \
  https://raw.githubusercontent.com/triole/ghwfe/master/bashrc/default.sh
RUN cat ${HOME}/tpl/add_to_bashrc >> ~/.bashrc
RUN chown -R "${USER}:${USER}" "${HOME}"

USER "${USER}"
# RDMO_INSTALL_URL must include a ref, e.g. git+https://github.com/<you>/rdmo.git@<branch>
# NOTE: do NOT shallow-clone (--depth) here: rdmo's version is derived by setuptools_scm
# from git tag history, so a shallow clone silently produces a bogus low version number
# (e.g. 0.1.0 instead of ~2.6.0), which then fails every XML import's required-version check
RUN if [ -n "${RDMO_INSTALL_URL}" ]; then \
      RDMO_GIT_URL="$(echo "${RDMO_INSTALL_URL}" | sed -e 's/^git+//' -e 's/@[^@]*$//')" && \
      RDMO_GIT_REF="$(echo "${RDMO_INSTALL_URL}" | sed -e 's/.*@//')" && \
      echo "Installing rdmo from ${RDMO_GIT_URL} @ ${RDMO_GIT_REF} (building frontend assets first)" && \
      git clone --branch "${RDMO_GIT_REF}" "${RDMO_GIT_URL}" /tmp/rdmo-src && \
      cd /tmp/rdmo-src && \
      npm ci && \
      npm run build:dist && \
      python -m pip install ".[allauth,postgres,gunicorn,openapi]" && \
      cd "${HOME}" && rm -rf /tmp/rdmo-src ; \
    else \
      python -m pip install "rdmo[allauth,postgres,gunicorn,openapi]==2.5.1" ; \
    fi

CMD ["/drun.sh"]
#CMD ["tail", "-f", "/dev/null"]
