# Pulumi Setup
```
export IMG="pulumi/pulumi-python:latest"
docker run -e PULUMI_ACCESS_TOKEN=pul-38a7bac35d5395681ca58e07ef1e9e09189dd91f \
-e PROXMOX_VE_USERNAME="pulumi@pve" \
-e PROXMOX_VE_PASSWORD="pulumi" \
-e PROXMOX_VE_ENDPOINT="https://192.168.1.13:8006" \
-v "$(pwd)":/pulumi/projects $IMG /bin/bash -c "cd /pulumi/projects/k3s-bootstrap && pip install -r ./requirements.txt && pulumi up -f -y -s dev"
```
```
export PROXMOX_VE_ENDPOINT="https://192.168.1.13:8006/"
export PROXMOX_VE_USERNAME="pulumi@pve"
export PROXMOX_VE_PASSWORD="pulumi"

```




# Setup Cloud-Init Ready Image
https://techno-tim.github.io/posts/cloud-init-cloud-image/
### Setup Image with guest tools and template
```
apt install libguestfs-tools -y
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
virt-customize -a noble-server-cloudimg-amd64.img --install qemu-guest-agent
qm create 8000 --memory 2048 --core 2 --name ubuntu-cloud --net0 virtio,bridge=vmbr0
qm importdisk 8000 noble-server-cloudimg-amd64.img local-lvm
qm set 8000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-8000-disk-0
qm set 8000 --ide2 local-lvm:cloudinit
qm set 8000 --boot c --bootdisk scsi0
qm set 8000 --serial0 socket --vga serial0
qm set 8000 --ipconfig0 ip=dhcp
qm resize 8000 scsi0 40G
qm template 8000
```