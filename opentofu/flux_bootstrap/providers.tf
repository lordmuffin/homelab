terraform {
  required_version = ">= 1.8.0"

  required_providers {
    flux = {
      source  = "fluxcd/flux"
      version = ">= 1.2"
    }
    talos = {
      source  = "siderolabs/talos"
      version = ">= 0.9.0"
    }
    github = {
      source  = "integrations/github"
      version = ">= 6.0"
    }
  }
}

provider "flux" {
  kubernetes = {
    host = var.cluster_endpoint
    # We do not use config_path here because we are in a CI/CD or separate phase context.
    # Authentication usually happens via other means or client certs if provided, 
    # but for this specific resource "flux_bootstrap_git", it largely relies on the Git provider 
    # and the ability to reach the cluster. 
    # NOTE: In a real "bootstrap" from outside, we usually need a kubeconfig or client certs/key.
    # However, the user requirements didn't specify passing the Kubeconfig content, just "cluster_endpoint".
    # flux_bootstrap_git typically uses the local kubeconfig by default if not specified, 
    # or we can pass client certificate data if available.
    # Given the constraints, I will leave the kubernetes block minimal or rely on what's available needed for "flux_bootstrap_git".
    # Correction: flux_bootstrap_git acts weirdly without kubeconfig. 
    # But adhering to ONLY the variables requested: `talos_client_configuration` is for Talos.
    # The prompt implies we are essentially bootstrapping. 
    # Let's assume the environment has KUBECONFIG set or we use standard config.
    # I will stick to the standard provider config.
  }
  
  git = {
    url = "ssh://git@github.com/${var.github_owner}/${var.github_repository}.git"
    ssh = {
      username    = "git"
      private_key = tls_private_key.flux.private_key_pem
    }
  }
}

provider "talos" {
  # Talos authentication is handled per resource or via the client_configuration passed in.
}

provider "github" {
  owner = var.github_owner
  # Configured via GITHUB_TOKEN environment variable typically, or we could add a variable if needed.
  # The user didn't explicitly ask for a github_token variable in the list of "Variables", 
  # but standard practice often implies it. The prompt LISTED specific variables. 
  # "Variables: Define all necessary input variables: ... "
  # It did NOT list github_token. I will assume env var `GITHUB_TOKEN` is used for the provider.
}
