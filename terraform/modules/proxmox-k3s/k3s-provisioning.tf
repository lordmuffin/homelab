# K3s cluster initialization for primary server
resource "null_resource" "k3s_init" {
  count = local.primary_server != null ? 1 : 0

  triggers = {
    server_id = try(
      local.all_vms[local.primary_server.key].id,
      ""
    )
  }

  connection {
    type        = "ssh"
    host        = local.primary_server.ip_address
    user        = var.vm_user
    private_key = var.ssh_private_key
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/templates/k3sup_install.sh"
    destination = "/tmp/k3sup_install.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/k3sup_install.sh",
      "/tmp/k3sup_install.sh install ${local.primary_server.tls_san} ${local.primary_server.ip_address} ${var.vm_user} '${var.ssh_private_key}' ${local.primary_server.tls_san}"
    ]
  }

  provisioner "file" {
    source      = "${path.module}/templates/cilium_install.sh"
    destination = "/tmp/cilium_install.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/cilium_install.sh",
      "/tmp/cilium_install.sh ${local.primary_server.tls_san}"
    ]
  }

  depends_on = [
    proxmox_virtual_environment_vm.k3s_nodes_pve,
    proxmox_virtual_environment_vm.k3s_nodes_pve2,
    proxmox_virtual_environment_vm.k3s_nodes_pve_nas_01
  ]
}

# Join additional servers to cluster
resource "null_resource" "k3s_server_join" {
  for_each = {
    for key, vm in local.server_vms : key => vm
    if vm.suffix != "001"
  }

  triggers = {
    server_id = try(
      local.all_vms[each.key].id,
      ""
    )
    primary_init = null_resource.k3s_init[0].id
  }

  connection {
    type        = "ssh"
    host        = each.value.ip_address
    user        = var.vm_user
    private_key = var.ssh_private_key
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/templates/k3sup_install.sh"
    destination = "/tmp/k3sup_install.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/k3sup_install.sh",
      "/tmp/k3sup_install.sh server ${each.value.tls_san} ${each.value.ip_address} ${var.vm_user} '${var.ssh_private_key}' ${each.value.tls_san}"
    ]
  }

  depends_on = [
    null_resource.k3s_init
  ]
}

# Join agents to cluster
resource "null_resource" "k3s_agent_join" {
  for_each = local.agent_vms

  triggers = {
    agent_id = try(
      local.all_vms[each.key].id,
      ""
    )
    primary_init = null_resource.k3s_init[0].id
  }

  connection {
    type        = "ssh"
    host        = each.value.ip_address
    user        = var.vm_user
    private_key = var.ssh_private_key
    timeout     = "5m"
  }

  provisioner "file" {
    source      = "${path.module}/templates/k3sup_install.sh"
    destination = "/tmp/k3sup_install.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/k3sup_install.sh",
      "/tmp/k3sup_install.sh agent ${local.primary_server.tls_san} ${each.value.ip_address} ${var.vm_user} '${var.ssh_private_key}' ${local.primary_server.tls_san}"
    ]
  }

  depends_on = [
    null_resource.k3s_init
  ]
}