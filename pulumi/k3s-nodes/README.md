# Pulumi Setup
```
export IMG="pulumi/pulumi-python:latest"
docker run -e PULUMI_ACCESS_TOKEN=$(op read "op://HomeLab/Pulumi Access Token/password") \
-e "PROXMOX_VE_PASSWORD=$(op read "op://HomeLab/proxmox pulumi/password")" \
-e "SSH_PUB_KEY=$(op read "op://HomeLab/onarfzninuoetwe2hh2ni7m52q/public key")" \
-e "SSH_PRIV_KEY=$(op read "op://HomeLab/onarfzninuoetwe2hh2ni7m52q/private key?ssh-format=openssh")" \
-e "VM_USER=$(op read "op://HomeLab/Ubuntu VM Default Creds/username")" \
-e "VM_PASS=$(op read "op://HomeLab/Ubuntu VM Default Creds/password")" \
-v "$(pwd)/pulumi:/pulumi/projects" $IMG /bin/bash -c "cd /pulumi/projects/$PROJECT && pip install -r ./requirements.txt && pulumi up -f -y -s dev"
```
export IMG="pulumi/pulumi-python:latest"
docker run -e PULUMI_ACCESS_TOKEN=$(op read "op://HomeLab/Pulumi Access Token/password") \
-e "PROXMOX_VE_PASSWORD=$(op read "op://HomeLab/proxmox pulumi/password")" \
-v "$(pwd)/pulumi:/pulumi/projects" $IMG /bin/bash -c "cd /pulumi/projects/$PROJECT && pulumi destroy --continue-on-error --yes -s dev"
```
export PROXMOX_VE_ENDPOINT="https://192.168.1.13:8006/"
export PROXMOX_VE_USERNAME="pulumi@pve"
export PROXMOX_VE_PASSWORD="pulumi"

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
wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img


virt-customize -a noble-server-cloudimg-amd64.img --install qemu-guest-agent
qm destroy 8000
qm create 8000 --memory 2048 --core 2 --name ubuntu-cloud-24.04 --ostype l26 --net0 virtio,bridge=vmbr0
qm importdisk 8000 noble-server-cloudimg-amd64.img local-lvm
qm set 8000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-8000-disk-0
qm set 8000 --scsi1 local-lvm:cloudinit
qm set 8000 --boot c --bootdisk scsi0
qm set 8000 --serial0 socket --vga serial0
qm set 8000 --agent enabled=1
qm resize 8000 scsi0 40G
qm template 8000
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
qm set 8000 --cicustom "user=local:snippets/template-user-data.yaml"