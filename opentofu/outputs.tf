output "talos_iso_url" {
  value = "https://factory.talos.dev/image/${talos_image_factory_schematic.this.id}/${var.talos_version}/nocloud-amd64.iso"
}
