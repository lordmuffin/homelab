# Production Environment Configuration
# IMPORTANT: This file contains sensitive information - never commit to version control

# Multi-Node Proxmox Configuration
# Replace the IP addresses and passwords with your actual values
proxmox_nodes_config = {
  # pve = {
  #   api_url      = "https://192.168.1.12:8006/api2/json"
  #   ip_address   = "192.168.1.12"
  #   token_id     = "terraform@pve!terraform"
  #   token_secret = "REPLACE_WITH_PVE_NAS_ROOT_PASSWORD"
  # }
  pve2 = {
    api_url      = "https://192.168.1.14:8006/api2/json"
    ip_address   = "192.168.1.14" 
    token_id     = "terraform@pve!terraform"
    token_secret = "56a7a10c-51be-4326-9b46-827267a38a42"
  }
  pve-nas-01 = {
    api_url      = "https://192.168.1.15:8006/api2/json"
    ip_address   = "192.168.1.15"
    token_id     = "terraform@pve!terraform"
    token_secret = "74bb1806-b743-459b-bfc1-3734f862030b"
  }
  pve4 = {
    api_url      = "https://192.168.1.37:8006/api2/json"
    ip_address   = "192.168.1.37"
    token_id     = "terraform@pve!terraform"
    token_secret = "b8fa41ff-c4f5-4d05-a805-58d3e60706f3"
  }
}

# Cluster Configuration  
cluster_name      = "k3s-prod"
vm_template_name  = "ubuntu-k3s-homelab-20250901-0909"

# Template VM ID Configuration (takes precedence over vm_template_name)
# Use the template IDs from your Packer builds for faster, more reliable cloning
# Uncomment and customize based on your actual template IDs:
vm_template_ids = {
  pve2       = 9000  # Template built for pve2 node
  pve-nas-01 = 9001  # Template built for pve-nas-01 node
  pve4       = 9002  # Template built for pve4 node
}

k3s_token        = "my-super-secure-k3s-production-token"

# Network Configuration
network_bridge  = "vmbr0"
network_gateway = "192.168.1.1"

# SSH Configuration - Add your actual public keys
ssh_public_keys = [
  "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDA8goFZngSeRbtWzKIdDNd+vJdjABjsRwSDrRdSg9jCHl2alXMHQTDf9O9u+adKZRsaXB4y28O5wdsCvyv23s6h3d5lIi85Xz8qeV0A/qJwrvvqzV+Bh0WK4aktaMxY1SbREKjsiuRBqRGGsuKv26rC0oa4XMdugmDmzSfiTs4iV61j/Y9HpyPVuvOeO+JC0sFXpcrrXqPQz9FyOqqtrFURai65ftCYYKjMci8zJ9MHBxAjKDQbmklTUqF4l+d1t4yTZNcy067JjfpU3SFJoOHblu24417FZNnUUhLS/V3hHxE5RZePVZM8vpVUGMHalQsI7dcxz/Tq0qIL6OCc9Z/v/pTg62Ha5Y4TXpi65hpwqOL5UBSXqOSMuGwhuKlsMwCwRQ8NSnr+175Irp0KNH8SPGtyiZ15SxBOifdIqy3qAZH/qFvlvda0a4lsVtZXjzrl7TREX6/2mwS1X///0C7vj3CnUcQ+R2mE8Fe4JkWepN1eDREXYZ3vENe/AzoBVMV3sbRi66dTD7E3vsijCflfBtj5hp977WMMWHbcXiGIF0gqRac1Dr6p7wUAZwLu1tXeGZFHQQOUwDmYllg7O9aA7lyPZ6r9CpLUFnV3a8Pfhj3wAxW5tV8dMcMystWLKo23lRyQsYwEym7TE/an4nNwe4RHBOxdihPfZawONn74w=="
]