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

### How to build image
```
docker build ./launcher/. --build-arg TARGETOS=linux --build-arg TARGETARCH=amd64 --build-arg KUBECTL_VERSION=1.28.2 --build-arg KUSTOMIZE_VERSION=5.4.1 -t homelab-launcher:v0.2.0
```
```
docker build ./launcher/. --build-arg TARGETOS=linux --build-arg TARGETARCH=amd64 --build-arg KUBECTL_VERSION=1.28.2 --build-arg KUSTOMIZE_VERSION=5.4.1 -t ghcr.io/lordmuffin/homelab-launcher:v0.2.0
```

### How to push image to ghcr
```
docker push ghcr.io/lordmuffin/homelab-launcher:latest
```

### How to use image:
```
docker run --rm -v ~/.kube/:/root/.kube:ro -v ${PWD}:/launcher -ti ghcr.io/lordmuffin/homelab-launcher:v0.2.0 task version
```

### Running inside k8s:
```
kubectl run homelab-launcher --restart=Never --rm -i --tty --image ghcr.io/lordmuffin/homelab-launcher:v0.2.0 -- /bin/bash
```
