#--------------------------------------------------------------
# Cloudspace and node pool configurations
#--------------------------------------------------------------

#--------------------------------------------------------------
# Existing cloud-homelab resources
#--------------------------------------------------------------
# Example of cloudspace resource.
resource "spot_cloudspace" "cloud-homelab" {
  cloudspace_name = "cloud-homelab"
  # You can find the available region names in the `regions` data source.
  region             = "us-central-ord-1"
  hacontrol_plane    = false
  preemption_webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
  wait_until_ready   = true
  kubernetes_version = "1.31.1"
  cni                = "cilium"
}

# Creates a spot node pool with an autoscaling pool of 3-8 servers of class gp.vs1.xlarge-ord (Extra Large).
resource "spot_spotnodepool" "autoscaling-bid" {
  cloudspace_name = resource.spot_cloudspace.cloud-homelab.cloudspace_name
  # You can find the available server classes in the `serverclasses` data source.
  server_class = "gp.vs1.xlarge-ord"
  bid_price    = 0.025


  # desired_server_count = 3

  autoscaling = {
    min_nodes = 3
    max_nodes = 6
  }

  labels = {
    "managed-by"         = "terraform"
  }
}

data "spot_kubeconfig" "cloud-homelab" {
  cloudspace_name = resource.spot_cloudspace.cloud-homelab.name
}

output "kubeconfig" {
  value = data.spot_kubeconfig.cloud-homelab.raw
}

#--------------------------------------------------------------
# Production cloud-homelab resources
#--------------------------------------------------------------
# Production cloudspace resource
resource "spot_cloudspace" "prod-cloud-homelab" {
  cloudspace_name = "prod-cloud-homelab"
  region             = "us-central-ord-1"
  hacontrol_plane    = false
  preemption_webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
  wait_until_ready   = true
  kubernetes_version = "1.31.1"
  cni                = "cilium"
}

# XLarge node pool for production environment (min 1, max 2)
resource "spot_spotnodepool" "prod-xlarge-pool" {
  cloudspace_name = resource.spot_cloudspace.prod-cloud-homelab.cloudspace_name
  server_class = "gp.vs1.xlarge-ord"
  bid_price    = 0.025  # Adjust bid price based on current market rates

  autoscaling = {
    min_nodes = 1
    max_nodes = 2
  }

  labels = {
    "managed-by" = "terraform"
    "env"        = "production"
    "pool-type"  = "xlarge"
  }
}

# Medium node pool for production environment (min 3, max 6)
resource "spot_spotnodepool" "prod-medium-pool" {
  cloudspace_name = resource.spot_cloudspace.prod-cloud-homelab.cloudspace_name
  server_class = "gp.vs1.medium-ord"
  bid_price    = 0.018  # Adjust bid price based on current market rates

  autoscaling = {
    min_nodes = 3
    max_nodes = 6
  }

  labels = {
    "managed-by" = "terraform"
    "env"        = "production"
    "pool-type"  = "medium"
  }
}

data "spot_kubeconfig" "prod-cloud-homelab" {
  cloudspace_name = resource.spot_cloudspace.prod-cloud-homelab.name
}

output "prod_kubeconfig" {
  value = data.spot_kubeconfig.prod-cloud-homelab.raw
}

#--------------------------------------------------------------
# Lab cloud-homelab resources
#--------------------------------------------------------------
# Lab environment cloudspace resource
resource "spot_cloudspace" "cloud-homelab" {
  cloudspace_name = "cloud-homelab"
  region             = "us-central-ord-1"
  hacontrol_plane    = false
  preemption_webhook = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
  wait_until_ready   = true
  kubernetes_version = "1.31.1"
  cni                = "cilium"
}

# XLarge node pool for lab environment (min 1, max 2)
resource "spot_spotnodepool" "lab-xlarge-pool" {
  cloudspace_name = resource.spot_cloudspace.cloud-homelab.cloudspace_name
  server_class = "gp.vs1.xlarge-ord"
  bid_price    = 0.020  # Lower bid price for lab environment

  autoscaling = {
    min_nodes = 1
    max_nodes = 2
  }

  labels = {
    "managed-by" = "terraform"
    "env"        = "lab"
    "pool-type"  = "xlarge"
  }
}

# Medium node pool for lab environment (min 3, max 6)
resource "spot_spotnodepool" "lab-medium-pool" {
  cloudspace_name = resource.spot_cloudspace.cloud-homelab.cloudspace_name
  server_class = "gp.vs1.medium-ord"
  bid_price    = 0.015  # Lower bid price for lab environment

  autoscaling = {
    min_nodes = 3
    max_nodes = 6
  }

  labels = {
    "managed-by" = "terraform"
    "env"        = "lab"
    "pool-type"  = "medium"
  }
}

data "spot_kubeconfig" "cloud-homelab" {
  cloudspace_name = resource.spot_cloudspace.cloud-homelab.name
}

output "lab_kubeconfig" {
  value = data.spot_kubeconfig.cloud-homelab.raw
}

#--------------------------------------------------------------
# Best Practices and Recommendations
#--------------------------------------------------------------
# 1. Bid Price Strategy:
#    - Set realistic bid prices based on current market rates
#    - Higher bid prices for production environments ensure better availability
#    - Lower bid prices for lab/dev environments optimize costs
#    - Monitor market prices regularly and adjust accordingly
#
# 2. Node Pool Configuration:
#    - Use multiple node pools with different sizes for workload flexibility
#    - XLarge nodes (8+ vCPUs, 16+ GB RAM) for resource-intensive applications
#    - Medium nodes for general workloads and scaling
#    - Use node selectors and taints/tolerations to target workloads to appropriate pools
#
# 3. Resource Optimization:
#    - Leverage autoscaling for cost efficiency
#    - Set lower min counts for non-production environments
#    - Configure proper resource requests/limits on pods
#    - Use Kubernetes Horizontal Pod Autoscaler (HPA) with node autoscaling
#
# 4. Operational Considerations:
#    - Implement Pod Disruption Budgets (PDBs) for graceful preemption handling
#    - Configure proper preemption webhooks for notifications (Slack/Teams/etc.)
#    - Use persistent volumes for stateful workloads
#    - Consider StatefulSets with proper termination grace periods
#
# 5. Cost Management:
#    - Take advantage of per-second billing
#    - Use the free bandwidth allowance (100GB/month per GB RAM)
#    - Consider node pools with different bid prices for different workload priorities
#    - Regularly review usage and adjust autoscaling parameters