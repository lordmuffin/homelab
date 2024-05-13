#!/bin/sh
echo "Starting IMG download."
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img
echo "Creating VM"
qm create 8000 --memory 2048 --core 2 --name ubuntu-cloud --net0 virtio,bridge=vmbr0
qm importdisk 8000 jammy-server-cloudimg-amd64.img local-lvm
qm set 8000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-8000-disk-0
qm set 8000 --ide2 local-lvm:cloudinit
qm set 8000 --boot c --bootdisk scsi0
qm set 8000 --serial0 socket --vga serial0
echo "Finished Configuring VM"
qm template 8000
echo "Finished Converting to Template