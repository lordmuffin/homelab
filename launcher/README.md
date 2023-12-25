# Launcher

## Purpose
The purpose of the `Dockerfile` is to build a launcher image that can be used to execute the homelab tasks.  This handles having all required pre-requisites installed for you.

## Contains
[X] kubectl
[X] kustomize
[X] yamllint - pip
[X] Taskfile
[X] terraform?
[X] kuotacalc
[] k3d?
[X] helm
[X] argocd

## Usage
```
docker build ./launcher/. --build-arg TARGETOS=linux --build-arg TARGETARCH=amd64 --build-arg KUBECTL_VERSION=1.28.2 --build-arg KUSTOMIZE_VERSION=5.3.0 -t homelab-launcher:v0.1.0
```
```
docker run --rm -v ~/.kube/:/root/.kube:ro -v ${PWD}:/launcher -ti homelab-launcher:v0.1.0 task version
```
