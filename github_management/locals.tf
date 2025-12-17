locals {
  # Load the JSON data
  raw_repos = jsondecode(file("${path.module}/repositories.json"))

  # All repositories for resource creation
  repos = local.raw_repos

  # Filtered list for ONLY existing repositories to be imported
  existing_repos = {
    for name, config in local.raw_repos :
    name => config
    if config.is_existing == true
  }
}
