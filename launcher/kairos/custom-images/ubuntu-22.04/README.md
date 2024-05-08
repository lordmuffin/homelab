# Upgrade Process

```
sudo kairos-agent upgrade --image ghcr.io/lordmuffin/custom-ubuntu-22.04-standard-amd64-generic-v2.4.3-k3sv1.28.2-k3s1:v0.0.4
```

```
docker build -t quay.io/vadimzharov/kairos:v1.28.0 -f Dockerfile.00
docker push quay.io/vadimzharov/kairos:v1.28.0
```