terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
  required_version = ">= 1.8"
}

provider "github" {
  # Configuration options primarily via environment variables (GITHUB_TOKEN, GITHUB_OWNER)
}

resource "github_repository" "repos" {
  for_each = local.repos

  name        = each.key
  description = each.value.description
  visibility  = each.value.visibility

  # Future-proofing: Enable template usage once a template repository is created.
  # dynamic "template" {
  #   for_each = can(each.value.template) ? [1] : []
  #   content {
  #     owner      = "my-org"
  #     repository = "my-template-repo"
  #   }
  # }
}
