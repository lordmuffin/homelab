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
Run first step to modify image on a dedicated machine (image-builder).  Then copy files to node, and run the last step.
```
#qemu-img resize $IMG +100M

apt install libguestfs-tools -y
# Ubuntu 22.04
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img
# Ubuntu 24.04
# wget https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img

export IMG=jammy-server-cloudimg-amd64.img
export IMG2=jammy-server-cloudimg-amd64-original.img
export VM_ID=8006
export VER=22.04

sudo qemu-img resize $IMG +1G
cp $IMG $IMG2
sudo virt-resize --expand /dev/sda1 $IMG2 $IMG
sudo virt-customize -a $IMG --run-command "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list"
sudo virt-customize -a $IMG --install qemu-guest-agent,nvidia-container-toolkit,nvidia-container-runtime
sudo virt-rescue --connect qemu:///system -a $IMG -i

# SUB COMMANDS FOR VIRT-RESCUE
chroot /sysroot
grub-install /dev/sda
df -h
exit
```
# Copy From Image-Builder
scp ubuntu@192.168.1.20:/home/ubuntu/jammy-server-cloudimg-amd64.img ./jammy-server-cloudimg-amd64.img
# Copy to PVE Node
scp ./jammy-server-cloudimg-amd64.img root@192.168.1.12:/root/jammy-server-cloudimg-amd64.img
```
export IMG=jammy-server-cloudimg-amd64.img
export VM_ID=8006
export VER=22.04
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