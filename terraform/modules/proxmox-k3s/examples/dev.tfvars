# Development environment configuration for Proxmox K3s cluster

# Proxmox providers configuration
providers = [
  {
    name        = "pve_provider"
    node_name   = "pve"
    endpoint    = "https://192.168.1.13:8006/"
    username    = "terraform@pve"
    insecure    = true
    hostpcis    = ""
  },
  {
    name        = "pve2_provider"
    node_name   = "pve2"
    endpoint    = "https://192.168.1.14:8006/"
    username    = "terraform@pve"
    insecure    = true
    hostpcis    = "gpu"
  },
  {
    name        = "pve_nas_01_provider"
    node_name   = "pve-nas-01"
    endpoint    = "https://192.168.1.15:8006/"
    username    = "terraform@pve"
    insecure    = true
    hostpcis    = ""
  }
]

# VM configurations
vms = [
  # K3s Server Node
  {
    name            = "pve-dev-server-nodes"
    count           = 1
    node_name       = "pve"
    vm_type         = "server"
    environment     = "dev"
    resource_name   = "lab"
    suffix          = "001"
    vm_id           = 1100
    tls_san         = "192.168.10.10"
    agent = {
      enabled = false
      type    = "virtio"
    }
    bios          = "seabios"
    ignore_changes = ["disks", "cdrom", "started"]
    cpu = {
      cores   = 4
      sockets = 1
    }
    cloud_init = {
      type         = "nocloud"
      interface    = "scsi1"
      datastore_id = "local-lvm"
      dns = {
        domain  = ""
        servers = ["1.1.1.1", "8.8.8.8"]
      }
      ip_configs = [
        {
          ipv4 = {
            address = "192.168.10.40/24"
            gateway = "192.168.10.1"
          }
        }
      ]
      user_account = {
        username = "ubuntu"
        password = "ubuntu"
        keys = [
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDA8goFZngSeRbtWzKIdDNd+vJdjABjsRwSDrRdSg9jCHl2alXMHQTDf9O9u+adKZRsaXB4y28O5wdsCvyv23s6h3d5lIi85Xz8qeV0A/qJwrvvqzV+Bh0WK4aktaMxY1SbREKjsiuRBqRGGsuKv26rC0oa4XMdugmDmzSfiTs4iV61j/Y9HpyPVuvOeO+JC0sFXpcrrXqPQz9FyOqqtrFURai65ftCYYKjMci8zJ9MHBxAjKDQbmklTUqF4l+d1t4yTZNcy067JjfpU3SFJoOHblu24417FZNnUUhLS/V3hHxE5RZePVZM8vpVUGMHalQsI7dcxz/Tq0qIL6OCc9Z/v/pTg62Ha5Y4TXpi65hpwqOL5UBSXqOSMuGwhuKlsMwCwRQ8NSnr+175Irp0KNH8SPGtyiZ15SxBOifdIqy3qAZH/qFvlvda0a4lsVtZXjzrl7TREX6/2mwS1X///0C7vj3CnUcQ+R2mE8Fe4JkWepN1eDREXYZ3vENe/AzoBVMV3sbRi66dTD7E3vsijCflfBtj5hp977WMMWHbcXiGIF0gqRac1Dr6p7wUAZwLu1tXeGZFHQQOUwDmYllg7O9aA7lyPZ6r9CpLUFnV3a8Pfhj3wAxW5tV8dMcMystWLKo23lRyQsYwEym7TE/an4nNwe4RHBOxdihPfZawONn74w=="
        ]
      }
    }
    disks = [
      {
        disk1 = {
          interface    = "scsi0"
          datastore_id = "local-lvm"
          size         = 40
          file_format  = "raw"
          cache        = "none"
        }
      }
    ]
    memory = {
      dedicated = 8192
    }
    network_devices = [
      {
        net1 = {
          bridge  = "vmbr0"
          model   = "virtio"
          vlan_id = 10
        }
      }
    ]
    on_boot = true
  },
  # K3s Agent Nodes
  {
    name            = "pve-dev-agent-nodes"
    count           = 2
    node_name       = "pve"
    vm_type         = "agent"
    environment     = "dev"
    resource_name   = "lab"
    suffix          = "001"
    vm_id           = 1110
    tls_san         = "192.168.10.10"
    agent = {
      enabled = false
      type    = "virtio"
    }
    bios          = "seabios"
    ignore_changes = ["disks", "cdrom", "started"]
    cpu = {
      cores   = 2
      sockets = 1
    }
    cloud_init = {
      type         = "nocloud"
      interface    = "scsi1"
      datastore_id = "local-lvm"
      dns = {
        domain  = ""
        servers = ["1.1.1.1", "8.8.8.8"]
      }
      ip_configs = [
        {
          ipv4 = {
            address = "192.168.10.50/24"
            gateway = "192.168.10.1"
          }
        }
      ]
      user_account = {
        username = "ubuntu"
        password = "ubuntu"
        keys = [
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDA8goFZngSeRbtWzKIdDNd+vJdjABjsRwSDrRdSg9jCHl2alXMHQTDf9O9u+adKZRsaXB4y28O5wdsCvyv23s6h3d5lIi85Xz8qeV0A/qJwrvvqzV+Bh0WK4aktaMxY1SbREKjsiuRBqRGGsuKv26rC0oa4XMdugmDmzSfiTs4iV61j/Y9HpyPVuvOeO+JC0sFXpcrrXqPQz9FyOqqtrFURai65ftCYYKjMci8zJ9MHBxAjKDQbmklTUqF4l+d1t4yTZNcy067JjfpU3SFJoOHblu24417FZNnUUhLS/V3hHxE5RZePVZM8vpVUGMHalQsI7dcxz/Tq0qIL6OCc9Z/v/pTg62Ha5Y4TXpi65hpwqOL5UBSXqOSMuGwhuKlsMwCwRQ8NSnr+175Irp0KNH8SPGtyiZ15SxBOifdIqy3qAZH/qFvlvda0a4lsVtZXjzrl7TREX6/2mwS1X///0C7vj3CnUcQ+R2mE8Fe4JkWepN1eDREXYZ3vENe/AzoBVMV3sbRi66dTD7E3vsijCflfBtj5hp977WMMWHbcXiGIF0gqRac1Dr6p7wUAZwLu1tXeGZFHQQOUwDmYllg7O9aA7lyPZ6r9CpLUFnV3a8Pfhj3wAxW5tV8dMcMystWLKo23lRyQsYwEym7TE/an4nNwe4RHBOxdihPfZawONn74w=="
        ]
      }
    }
    disks = [
      {
        disk1 = {
          interface    = "scsi0"
          datastore_id = "local-lvm"
          size         = 20
          file_format  = "raw"
          cache        = "none"
        }
      }
    ]
    memory = {
      dedicated = 4096
    }
    network_devices = [
      {
        net1 = {
          bridge  = "vmbr0"
          model   = "virtio"
          vlan_id = 10
        }
      }
    ]
    on_boot = true
  },
  # GPU Agent Node
  {
    name            = "pve2-dev-gpu-agent"
    count           = 1
    node_name       = "pve2"
    vm_type         = "gpu-agent"
    environment     = "dev"
    resource_name   = "lab"
    suffix          = "001"
    vm_id           = 1120
    tls_san         = "192.168.10.10"
    agent = {
      enabled = false
      type    = "virtio"
    }
    bios          = "seabios"
    ignore_changes = ["disks", "cdrom", "started"]
    cpu = {
      cores   = 4
      sockets = 1
    }
    cloud_init = {
      type         = "nocloud"
      interface    = "scsi1"
      datastore_id = "local-lvm"
      dns = {
        domain  = ""
        servers = ["1.1.1.1", "8.8.8.8"]
      }
      ip_configs = [
        {
          ipv4 = {
            address = "192.168.10.60/24"
            gateway = "192.168.10.1"
          }
        }
      ]
      user_account = {
        username = "ubuntu"
        password = "ubuntu"
        keys = [
          "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDA8goFZngSeRbtWzKIdDNd+vJdjABjsRwSDrRdSg9jCHl2alXMHQTDf9O9u+adKZRsaXB4y28O5wdsCvyv23s6h3d5lIi85Xz8qeV0A/qJwrvvqzV+Bh0WK4aktaMxY1SbREKjsiuRBqRGGsuKv26rC0oa4XMdugmDmzSfiTs4iV61j/Y9HpyPVuvOeO+JC0sFXpcrrXqPQz9FyOqqtrFURai65ftCYYKjMci8zJ9MHBxAjKDQbmklTUqF4l+d1t4yTZNcy067JjfpU3SFJoOHblu24417FZNnUUhLS/V3hHxE5RZePVZM8vpVUGMHalQsI7dcxz/Tq0qIL6OCc9Z/v/pTg62Ha5Y4TXpi65hpwqOL5UBSXqOSMuGwhuKlsMwCwRQ8NSnr+175Irp0KNH8SPGtyiZ15SxBOifdIqy3qAZH/qFvlvda0a4lsVtZXjzrl7TREX6/2mwS1X///0C7vj3CnUcQ+R2mE8Fe4JkWepN1eDREXYZ3vENe/AzoBVMV3sbRi66dTD7E3vsijCflfBtj5hp977WMMWHbcXiGIF0gqRac1Dr6p7wUAZwLu1tXeGZFHQQOUwDmYllg7O9aA7lyPZ6r9CpLUFnV3a8Pfhj3wAxW5tV8dMcMystWLKo23lRyQsYwEym7TE/an4nNwe4RHBOxdihPfZawONn74w=="
        ]
      }
    }
    disks = [
      {
        disk1 = {
          interface    = "scsi0"
          datastore_id = "local-lvm"
          size         = 40
          file_format  = "raw"
          cache        = "none"
        }
      }
    ]
    memory = {
      dedicated = 8192
    }
    network_devices = [
      {
        net1 = {
          bridge  = "vmbr0"
          model   = "virtio"
          vlan_id = 10
        }
      }
    ]
    on_boot = true
  }
]

# Template and K3s configuration
template_vm_id = 8006
k3s_version = "v1.28.2+k3s1"
k3s_options = "--flannel-backend=none --no-flannel --disable-kube-proxy --disable servicelb --disable-network-policy"

# VM defaults
vm_user = "ubuntu"