FROM curlimages/curl:7.83.1 AS downloader

ARG TARGETOS
ARG TARGETARCH
ARG KUBECTL_VERSION
ARG KUSTOMIZE_VERSION

WORKDIR /downloads

RUN set -ex; \
    curl -fL https://storage.googleapis.com/kubernetes-release/release/v${KUBECTL_VERSION}/bin/${TARGETOS}/${TARGETARCH}/kubectl -o kubectl && \
    chmod +x kubectl

RUN set -ex; \
    curl -fL https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v${KUSTOMIZE_VERSION}/kustomize_v${KUSTOMIZE_VERSION}_${TARGETOS}_${TARGETARCH}.tar.gz | tar xz && \
    chmod +x kustomize

RUN set -ex; \
    curl -fL https://get.helm.sh/helm-v3.13.3-linux-arm64.tar.gz | tar xz && \
    chmod +x ./linux-arm64/helm

RUN set -ex; \
    curl -fL https://github.com/yannh/kubeconform/releases/download/v0.6.4/kubeconform-linux-amd64.tar.gz | tar xz && \
    chmod +x kubeconform

RUN set -ex; \
    curl -fLO https://github.com/alexellis/k3sup/releases/download/0.13.5/k3sup && \
    chmod +x k3sup

RUN set -ex; \
    sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b task && \
    chmod +x ./task/task

RUN set -ex; \
    curl -fLO "https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip" && \
    unzip terraform_1.6.6_linux_amd64.zip && rm terraform_1.6.6_linux_amd64.zip && \
    chmod +x terraform

RUN set -ex; \
    curl -fLO "https://github.com/postfinance/kuota-calc/releases/download/v0.2.2/kuota-calc_linux_x86_64.zip" && \
    unzip -o kuota-calc_linux_x86_64.zip && rm kuota-calc_linux_x86_64.zip && \
    chmod +x kuota-calc

RUN set -ex; \
    curl -fLO "https://releases.hashicorp.com/vault/1.15.4/vault_1.15.4_linux_amd64.zip" && \
    unzip -o vault_1.15.4_linux_amd64.zip && rm vault_1.15.4_linux_amd64.zip && \
    chmod +x vault

RUN set -ex; \
    curl -sLO https://github.com/argoproj/argo-workflows/releases/download/v3.5.2/argo-linux-amd64.gz && \
    gunzip argo-linux-amd64.gz && \
    chmod +x argo-linux-amd64


# Runtime
FROM alpine:3.16.0 AS runtime

LABEL maintainer="LINE Open Source <dl_oss_dev@linecorp.com>"

RUN apk update && apk add --no-cache python3 py3-pip git jq openssl
RUN pip install yamllint
RUN mkdir /launcher

WORKDIR /launcher

COPY --from=downloader /usr/bin/curl /usr/local/bin/curl
COPY --from=downloader /downloads/kubectl /usr/local/bin/kubectl
COPY --from=downloader /downloads/kustomize /usr/local/bin/kustomize
COPY --from=downloader /downloads/linux-arm64/helm /usr/local/bin/helm
COPY --from=downloader /downloads/kubeconform /usr/local/bin/kubeconform
COPY --from=downloader /downloads/k3sup /usr/local/bin/k3sup
COPY --from=downloader /downloads/task/task /usr/local/bin/task
COPY --from=downloader /downloads/terraform /usr/local/bin/terraform
COPY --from=downloader /downloads/kuota-calc /usr/local/bin/kuota-calc
COPY --from=downloader /downloads/vault /usr/local/bin/vault
COPY --from=downloader /downloads/argo-linux-amd64 /usr/local/bin/argocd

# Test
FROM runtime AS test

RUN set -ex; kubectl && kustomize && task --version && helm version && \
    terraform --version && kuota-calc --version && argocd version && yamllint -v && \
    kubeconform -v && k3sup version
