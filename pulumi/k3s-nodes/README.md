# Pulumi Setup
```
export IMG="pulumi/pulumi-python:latest"
docker run --rm -e PULUMI_ACCESS_TOKEN=$(op read "op://HomeLab/Pulumi Access Token/password") \
-e "GITHUB_TOKEN=$(op read "op://Private/GitHub General Access Token/password")" \
-e "PROXMOX_VE_PASSWORD=$(op read "op://HomeLab/proxmox pulumi/password")" \
-e "SSH_PUB_KEY=$(op read "op://HomeLab/onarfzninuoetwe2hh2ni7m52q/public key")" \
-e "SSH_PRIV_KEY=$(op read "op://HomeLab/onarfzninuoetwe2hh2ni7m52q/private key?ssh-format=openssh")" \
-e "VM_USER=$(op read "op://HomeLab/Ubuntu VM Default Creds/username")" \
-e "VM_PASS=$(op read "op://HomeLab/Ubuntu VM Default Creds/password")" \
-v "$(pwd)/pulumi:/pulumi/projects" $IMG /bin/bash -c "cd /pulumi/projects/k3s-nodes && pip install -r ./requirements.txt && pulumi up -f -y -s dev"
```
```
export IMG="pulumi/pulumi-python:latest"
docker run --rm -e PULUMI_ACCESS_TOKEN=$(op read "op://HomeLab/Pulumi Access Token/password") \
-e "PROXMOX_VE_PASSWORD=$(op read "op://HomeLab/proxmox pulumi/password")" \
-v "$(pwd)/pulumi:/pulumi/projects" $IMG /bin/bash -c "cd /pulumi/projects/k3s-nodes && pulumi destroy --continue-on-error --yes -s dev"
```
```
export IMG="pulumi/pulumi-python:latest"
docker run --rm -e PULUMI_ACCESS_TOKEN=$(op read "op://HomeLab/Pulumi Access Token/password") \
-e "PROXMOX_VE_PASSWORD=$(op read "op://HomeLab/proxmox pulumi/password")" \
-v "$(pwd)/pulumi:/pulumi/projects" $IMG /bin/bash -c "cd /pulumi/projects/k3s-nodes && pulumi refresh --yes -s dev"
```
# K3Sup Commands
```
export K3S_VERSION="v1.28.2+k3s1"
export K3S_OPTIONS="--flannel-backend=none --no-flannel --disable-kube-proxy --disable servicelb --disable-network-policy --tls-san=192.168.10.10"
export USER="ubuntu"
k3sup install --cluster --ip $(govc vm.ip /42can/vm/cilium0) --user $UBUNTU --local-path ~/.kube/cilium.yaml --k3s-version $K3S_VERSION --k3s-extra-args $K3S_OPTIONS
k3sup join --ip $(govc vm.ip /42can/vm/cilium1) --server-ip $(govc vm.ip /42can/vm/cilium0) --server --server-user nick --user $UBUNTU --k3s-version $K3S_VERSION --k3s-extra-args $K3S_OPTIONS
k3sup join --ip $(govc vm.ip /42can/vm/cilium2) --server-ip $(govc vm.ip /42can/vm/cilium0) --server --server-user nick --user $UBUNTU --k3s-version $K3S_VERSION --k3s-extra-args $K3S_OPTIONS
```



# Setup Cloud-Init Ready Image
https://techno-tim.github.io/posts/cloud-init-cloud-image/
### Setup Image with guest tools and template
Run this on pve nodes directly (Future State: Write a remote script? Pulumi?)
```
apt install libguestfs-tools -y
# Ubuntu 22.04
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img
# Ubuntu 24.04
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

export IMG=jammy-server-cloudimg-amd64.img
export VM_ID=8001
export VER=22.04

virt-customize -a $IMG --install qemu-guest-agent
qm destroy $VM_ID
qm create $VM_ID --memory 2048 --core 2 --name ubuntu-cloud-$VER --ostype l26 --net0 virtio,bridge=vmbr0
qm importdisk $VM_ID $IMG local-lvm
qm set $VM_ID --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-$VM_ID-disk-0
qm set $VM_ID --scsi1 local-lvm:cloudinit
qm set $VM_ID --boot c --bootdisk scsi0
qm set $VM_ID --serial0 socket --vga serial0
qm set $VM_ID --agent enabled=1
qm resize $VM_ID scsi0 40G
qm template $VM_ID

```

# NOT USED::
cat << EOF | tee /var/lib/vz/snippets/template-user-data.yaml
#cloud-config
runcmd:
    - apt-get update
    - systemctl enable ssh
    - reboot
# Taken from https://forum.proxmox.com/threads/combining-custom-cloud-init-with-auto-generated.59008/page-3#post-428772
EOF
qm set $VM_ID --cicustom "user=local:snippets/template-user-data.yaml"