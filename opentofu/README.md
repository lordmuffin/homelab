# Talos HA Cluster on Proxmox with OpenTofu

This project provides an automated Infrastructure-as-Code (IaC) solution to deploy a High Availability (3-node) Talos Linux Kubernetes cluster on Proxmox VE using OpenTofu.

It handles:
*   **Infrastructure Provisioning**: Creating VMs on Proxmox.
*   **Configuration Generation**: Generating Talos machine secrets and configurations with a Virtual IP (VIP).
*   **ISO Generation**: Dynamically creating a Talos ISO with `qemu-guest-agent` and `iscsi-tools` extensions.
*   **CNI Preparation**: Disabling the default CNI to allow for Cilium installation.

## Prerequisites

*   **OpenTofu**: [Install OpenTofu](https://opentofu.org/docs/intro/install/) (v1.6+).
*   **Talosctl**: [Install talosctl](https://www.talos.dev/v1.8/learn-more/talosctl/) (matching the Talos version, e.g., v1.8.x).
*   **Proxmox VE**: A Proxmox host with:
    *   API Token created for a user with sufficient privileges (VM.Allocate, Datastore.AllocateSpace, etc.).
    *   A storage pool (e.g., `local-lvm`) available.
    *   A network bridge (e.g., `vmbr0`) with access to the DHCP network.
*   **Cilium CLI** (Optional, for local install): [Install Cilium CLI](https://docs.cilium.io/en/stable/gettingstarted/k8s-install-default/#install-the-cilium-cli).

## Configuration

1.  **Navigate to the directory**:
    ```bash
    cd opentofu
    ```

2.  **Create a `terraform.tfvars` file**:
    Create a file named `terraform.tfvars` to store your sensitive configuration. **Do not commit this file.**

    ```hcl
    # Proxmox Connection
    pm_api_url      = "https://192.168.1.10:8006/api2/json"
    pm_token_id     = "user@pam!tokenid"
    pm_token_secret = "your-api-token-secret"
    target_node     = "pve-host-01"

    # Network
    vip_ip          = "192.168.1.50" # Pick a static, unused IP in your subnet

    # Cluster Customization
    cluster_name    = "talos-ha-cluster"
    talos_version   = "v1.8.1"
    ```

    Alternatively, you can export these as environment variables (e.g., `TF_VAR_pm_api_url`).

## Deployment Workflow

1.  **Initialize OpenTofu**:
    ```bash
    tofu init
    ```

2.  **Review the Plan**:
    ```bash
    tofu plan
    ```

3.  **Apply the Configuration**:
    ```bash
    tofu apply
    ```
    *   This will download the Talos ISO, upload it to Proxmox, create the VMs, and attach the generated configuration.
    *   **Wait** for the VMs to boot. It may take a minute for the QEMU Guest Agent to report IP addresses.

## Bootstrapping the Cluster

Once `tofu apply` completes, you will see several outputs.

1.  **Get the Control Plane IP**:
    Identify the IP address for bootstrapping from the output:
    ```bash
    BOOTSTRAP_IP=$(tofu output -raw control_plane_bootstrap_ip)
    echo "Bootstrap IP: $BOOTSTRAP_IP"
    ```

2.  **Generate `talosconfig` and `kubeconfig`**:
    The OpenTofu run generates the client configuration. However, it's often easier to merge it into your local config or generate a new one if you have the secrets.

    For simplicity, you can construct a `talosconfig` using the generated secrets (advanced) or just use the generated config output if you captured it.

    **Recommended**: Configure `talosctl` to point to the new node.
    ```bash
    # Extract the generated talos config (if you didn't output it to a file, you might need to construct it or use the IP directly)
    # Since we output the raw config in the state, we can extract it:
    tofu output -raw talos_config > talosconfig
    export TALOSCONFIG=$(pwd)/talosconfig

    # Update the endpoint to point to the specific node for bootstrapping (VIP might not be up yet)
    talosctl config endpoint $BOOTSTRAP_IP
    talosctl config node $BOOTSTRAP_IP
    ```

3.  **Bootstrap**:
    ```bash
    talosctl bootstrap
    ```

4.  **Retrieve Kubeconfig**:
    Once the bootstrap is complete and etcd is healthy:
    ```bash
    talosctl kubeconfig .
    ```
    This creates a `kubeconfig` file in the current directory.

## Post-Deployment: Install Cilium

The cluster is deployed with `cni.name: none`, so nodes will remain in a `NotReady` state until a CNI is installed.

1.  **Run the Installation Script**:
    ```bash
    # Ensure you have the kubeconfig from the previous step
    chmod +x scripts/install_cilium.sh
    ./scripts/install_cilium.sh ./kubeconfig
    ```

2.  **Verify Status**:
    ```bash
    export KUBECONFIG=./kubeconfig
    kubectl get nodes
    cilium status
    ```

## Verification

*   **Check Talos Health**:
    ```bash
    talosctl health
    ```
*   **Check Kubernetes Nodes**:
    ```bash
    kubectl get nodes -o wide
    ```

## Security Note

This plan outputs sensitive secrets (Talos machine secrets, Kubeconfig data) to the OpenTofu state file. **Ensure your state file is stored securely** (e.g., using a remote backend with encryption) and strict permissions are applied to your local directory.
