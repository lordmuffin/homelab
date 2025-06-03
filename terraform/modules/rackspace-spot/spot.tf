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

# Creates a spot node pool with an autoscaling pool of 3-8 servers of class gp.vs1.large-dfw.
resource "spot_spotnodepool" "autoscaling-bid" {
  cloudspace_name = resource.spot_cloudspace.cloud-homelab.cloudspace_name
  # You can find the available server classes in the `serverclasses` data source.
  server_class = "ch.vs1.large-ord"
  bid_price    = 0.010


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