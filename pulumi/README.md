# Pulumi Setup
```
export IMG="pulumi/pulumi-python:latest"
docker run -e PULUMI_ACCESS_TOKEN=pul-17fe914ed5c67f321bcc03184db3166451fb83e9 \
-e PROXMOX_VE_USERNAME="pulumi@pve" \
-e PROXMOX_VE_PASSWORD="pulumi" \
-e PROXMOX_VE_ENDPOINT="https://192.168.1.13:8006/" \
-v "$(pwd)":/pulumi/projects $IMG /bin/bash -c "pulumi preview -s dev"
```
```
export IMG="pulumi/pulumi-python:latest"
docker run -e PULUMI_ACCESS_TOKEN=pul-17fe914ed5c67f321bcc03184db3166451fb83e9 \
-e PROXMOX_VE_USERNAME="pulumi@pve" \
-e PROXMOX_VE_PASSWORD="pulumi" \
-e PROXMOX_VE_ENDPOINT="https://192.168.1.13:8006" \
-v "$(pwd)":/pulumi/projects $IMG /bin/bash -c "curl https://github.com/muhlba91/pulumi-proxmoxve/releases/download/v6.5.1/pulumi-resource-proxmoxve-v6.5.1-linux-amd64.tar.gz -o /pulumi/projects/pulumi-resource-proxmoxve-v6.5.1-linux-amd64.tar.gz && pulumi plugin install resource proxmoxve 6.5.1 -f /pulumi/projects/pulumi-resource-proxmoxve-v6.5.1-linux-amd64.tar.gz && pulumi preview -s dev && pulumi up -f -y -s dev"
```
```
export IMG="pulumi/pulumi-python:latest"
docker run -e PULUMI_ACCESS_TOKEN=pul-17fe914ed5c67f321bcc03184db3166451fb83e9 \
-e PROXMOX_VE_USERNAME="pulumi@pve" \
-e PROXMOX_VE_PASSWORD="pulumi" \
-e PROXMOX_VE_ENDPOINT="https://192.168.1.13:8006" \
-v "$(pwd)":/pulumi/projects $IMG /bin/bash -c "pip install -r /pulumi/projects/requirements.txt && pulumi preview -s dev && pulumi up -f -y -s dev"
```
```
export PROXMOX_VE_ENDPOINT="https://192.168.1.13:8006/"
export PROXMOX_VE_USERNAME="pulumi@pve"
export PROXMOX_VE_PASSWORD="pulumi"

```