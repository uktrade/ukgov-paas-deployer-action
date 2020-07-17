FROM debian:buster-slim

ENV PACKAGES "unzip curl git sudo bash jq wget iputils-ping gnupg2 python3.7 python3-distutils python3-pip"
ENV CF_CLI_VERSION "6.47.2"
ENV PIP_PACKAGES "hvac python-dotenv requests cloudfoundry-client django-environ"
ENV CF_AUTOPILOT_VERSION="0.0.4"
ENV GITHUB_RUNNER_VERSION="2.267.1"
ENV RUNNER_NAME "runner"
ENV GITHUB_PAT ""
ENV GITHUB_OWNER ""
ENV GITHUB_REPOSITORY ""
ENV RUNNER_WORKDIR "_work"
ENV RUNNER_LABELS ""

RUN apt-get update \
    && apt-get install -y $PACKAGES \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m github \
    && echo "github ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && echo "alias python=python3" >> /home/github/.profile \
    && echo "alias pip=pip3" >> /home/github/.profile \
    && pip3 install $PIP_PACKAGES

#Install cf-cli
RUN curl -L "https://cli.run.pivotal.io/stable?release=linux64-binary&version=${CF_CLI_VERSION}" | tar -zx -C /usr/local/bin \
    && cf install-plugin https://github.com/contraband/autopilot/releases/download/${CF_AUTOPILOT_VERSION}/autopilot-linux -f

USER github
WORKDIR /home/github

ADD vault.py /home/github/vault.py

RUN curl -Ls https://github.com/actions/runner/releases/download/v${GITHUB_RUNNER_VERSION}/actions-runner-linux-x64-${GITHUB_RUNNER_VERSION}.tar.gz | tar xz \
    && sudo ./bin/installdependencies.sh

COPY --chown=github:github entrypoint.sh ./entrypoint.sh
RUN sudo chmod u+x ./entrypoint.sh

ENTRYPOINT ["/home/github/entrypoint.sh"]
