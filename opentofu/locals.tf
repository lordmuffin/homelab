locals {
  cluster_name = coalesce(var.cluster_name, "${var.cluster_env}-${var.cluster_loc}-${var.cluster_purpose}")
}
