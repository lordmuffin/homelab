import {
  for_each = local.existing_repos

  # The ID for a GitHub repository resource is "owner/repo" or just "repo" 
  # depending on context, but usually the name works if implied by the provider config.
  # Assuming the provider defaults to the authenticated user/org. 
  # Using just the name here as the unique ID for the import.
  id = each.key

  # The resource address to import into
  to = github_repository.repos[each.key]
}
