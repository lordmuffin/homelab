# Proxmox Host Settings
```
pveum useradd packer@pve
pveum passwd packer@pve
pveum roleadd Packer -privs "VM.Config.Disk VM.Config.CPU VM.Config.Memory Datastore.AllocateSpace Sys.Modify VM.Config.Options VM.Allocate VM.Audit VM.Console VM.Config.CDROM VM.Config.Network VM.PowerMgmt VM.Config.HWType VM.Monitor"
pveum aclmod / -user packer@pve -role Packer


pveum useradd pulumi@pve
pveum passwd pulumi@pve
pveum group add pulumi -comment "Pulumi Administrators"
pveum acl modify / -group pulumi -role PVEAdmin
pveum user modify pulumi@pve -group pulumi

```
```
export PROXMOX_USERNAME=$(op read "op://HomeLab/pve_nas_01 packer token/username")
export PROXMOX_TOKEN=$(op read "op://HomeLab/pve_nas_01 packer token/password")
export PROXMOX_URL=$(op read "op://HomeLab/pve_nas_01 packer token/url")
packer build -var-file=secrets.json ./ubuntu-22.04/ubuntu.json
```


```
export IMG="hashicorp/packer:latest"
docker run --rm -v "$(pwd)/packer:/packer" \
-e PACKER_PLUGIN_PATH=/packer/plugins \
-w /packer $IMG init proxmox.pkr.hcl
docker run --rm -v "$(pwd)/packer:/packer" \
-e PACKER_PLUGIN_PATH=/packer/plugins \
-w /packer $IMG build -var-file=secrets.json ./ubuntu-22.04/ubuntu.json
```

```
packer build -var-file=secrets.json ubuntu.json
```

secrets.json
```
{
  "proxmox_username": "packer@pve",
  "proxmox_password": "fQk9f5Wd22aBgv"
}
```

secrets.json override
```
{
  "proxmox_vm_id": "201",
  "proxmox_template_name": "ubuntu-22.04",
  "ubuntu_iso_file": "ubuntu-22.04-live-server-amd64.iso"
}
```
