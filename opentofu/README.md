# Talos HA Cluster on Proxmox with OpenTofu

This project provides an automated Infrastructure-as-Code (IaC) solution to deploy a High Availability (3-node) Talos Linux Kubernetes cluster on Proxmox VE using OpenTofu.

It handles:
*   **Infrastructure Provisioning**: Creating VMs on Proxmox.
*   **Configuration Generation**: Generating Talos machine secrets and configurations with a Virtual IP (VIP).
*   **ISO Generation**: Dynamically creating a Talos ISO with `qemu-guest-agent` and `iscsi-tools` extensions.
*   **CNI Preparation**: Disabling the default CNI to allow for Cilium installation.

## Prerequisites

### 1. Proxmox User Setup

Run the setup script on your **Proxmox host** to create the OpenTofu user and API token:

```bash
# SSH into your Proxmox host
ssh root@192.168.10.5

# Download and run the setup script
curl -sSL https://raw.githubusercontent.com/yourusername/homelab/main/opentofu/scripts/setup-proxmox-user.sh | bash

# OR if you have the repo cloned:
cd /path/to/homelab/opentofu/scripts
chmod +x setup-proxmox-user.sh
./setup-proxmox-user.sh
```

The script will output a `proxmox_api_token` value - **save this for your `terraform.tfvars`**.

### 2. Local Tools

*   **OpenTofu**: [Install OpenTofu](https://opentofu.org/docs/intro/install/) (v1.6+).
*   **Talosctl**: [Install talosctl](https://www.talos.dev/v1.8/learn-more/talosctl/) (matching the Talos version, e.g., v1.8.x).
*   **Cilium CLI** (Optional, for local install): [Install Cilium CLI](https://docs.cilium.io/en/stable/gettingstarted/k8s-install-default/#install-the-cilium-cli).

### 3. Proxmox Requirements
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
    proxmox_endpoint  = "http://192.168.1.10:8006/" # Check if your Proxmox uses http or https
    proxmox_api_token = "user@pam!tokenid=uuid" # Full token string
    proxmox_node      = "pve-host-01"

    # Network
    cluster_vip       = "192.168.1.50" # Pick a static, unused IP in your subnet
    gateway           = "192.168.1.1"
    control_plane_ips = ["192.168.1.10", "192.168.1.11", "192.168.1.12"]

    # Cluster Customization
    cluster_name      = "talos-ha-cluster"
    talos_version     = "v1.8.1"
    ```

    Alternatively, you can export these as environment variables (e.g., `TF_VAR_pm_api_url`).

3.  **Export Backend Credentials**:
    Export your secrets using the custom variables:

    **Bash:**
    ```bash
    export TOFU_ACCESS_KEY_ID="<your-access-key>"
    export TOFU_SECRET_ACCESS_KEY="<your-secret-key>"
    ```

    **PowerShell:**
    ```powershell
    $Env:TOFU_ACCESS_KEY_ID="<your-access-key>"
    $Env:TOFU_SECRET_ACCESS_KEY="<your-secret-key>"
    ```

## Deployment Workflow

1.  **Initialize OpenTofu**:
    Initialize the backend passing the secrets:

    **Bash:**
    ```bash
    tofu init \
      -backend-config="access_key=${TOFU_ACCESS_KEY_ID}" \
      -backend-config="secret_key=${TOFU_SECRET_ACCESS_KEY}"
    ```

    **PowerShell:**
    ```powershell
    tofu init `
      -backend-config="access_key=$Env:TOFU_ACCESS_KEY_ID" `
      -backend-config="secret_key=$Env:TOFU_SECRET_ACCESS_KEY"
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
    **Bash:**
    ```bash
    BOOTSTRAP_IP=$(tofu output -raw control_plane_bootstrap_ip)
    echo "Bootstrap IP: $BOOTSTRAP_IP"
    ```

    **PowerShell:**
    ```powershell
    $BOOTSTRAP_IP = tofu output -raw control_plane_bootstrap_ip
    Write-Host "Bootstrap IP: $BOOTSTRAP_IP"
    ```

2.  **Generate `talosconfig` and `kubeconfig`**:
    The OpenTofu run generates the client configuration. However, it's often easier to merge it into your local config or generate a new one if you have the secrets.

    For simplicity, you can construct a `talosconfig` using the generated secrets (advanced) or just use the generated config output if you captured it.

    **Recommended**: Configure `talosctl` to point to the new node.
    **Bash:**
    ```bash
    # Extract the generated talos config
    tofu output -raw talos_config > talosconfig
    export TALOSCONFIG=$(pwd)/talosconfig

    # Update the endpoint to point to the specific node for bootstrapping (VIP might not be up yet)
    talosctl config endpoint $BOOTSTRAP_IP
    talosctl config node $BOOTSTRAP_IP
    ```

    **PowerShell:**
    ```powershell
    # Extract the generated talos config
    tofu output -raw talos_config | Out-File -Encoding utf8 talosconfig
    $Env:TALOSCONFIG = "$PWD/talosconfig"

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
    **Bash:**
    ```bash
    # Ensure you have the kubeconfig from the previous step
    chmod +x scripts/install_cilium.sh
    ./scripts/install_cilium.sh ./kubeconfig
    ```

    **PowerShell:**
    ```powershell
    # PowerShell support for the install script is not currently available.
    # Please run in a Bash environment (WSL, Git Bash) or manually install Cilium.
    ```

2.  **Verify Status**:
    **Bash:**
    ```bash
    export KUBECONFIG=./kubeconfig
    kubectl get nodes
    cilium status
    ```

    **PowerShell:**
    ```powershell
    $Env:KUBECONFIG = "./kubeconfig"
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

# 🏷️ Kubernetes Naming Convention

This document defines the standard naming convention for all Kubernetes clusters and nodes within the homelab environment, ensuring consistency, predictability, and ease of management across on-premise and multiple cloud providers.

## Principles

1.  **Clarity:** Names are easily readable and parseable by humans.
2.  **Uniqueness:** Every resource has a unique identifier based on its location and purpose.
3.  **Predictability:** New resources can be named consistently using the defined components.

## Cluster Naming Pattern

All cluster names must follow the three-part structure separated by hyphens (`-`):

$$\text{[ENV]}-\text{[LOC]}-\text{[PURPOSE]}$$

### 1. ENV (Environment)

| Value | Description |
| :--- | :--- |
| **p** | **Production:** Critical, stable, highly available services. |
| **np** | **Non-Production:** Staging, UAT, and non-critical services. |
| **dev** | **Development:** Testing, sandbox environments, and new features. |

### 2. LOC (Location/Provider)

This identifies where the cluster physically resides.

| Value | Provider |
| :--- | :--- |
| **home** | On-Premise/House (Primary Homelab) |
| **aws** | Amazon Web Services |
| **az** | Microsoft Azure |
| **gcp** | Google Cloud Platform |
| **lnd** | Linode |
| **rs** | Rackspace |

### 3. PURPOSE (User-Defined)

A short, descriptive name for the cluster's function.
* **Default:** `homelab` (Used for general-purpose clusters).
* **Examples:** `web`, `jenkins`, `db-core`, `storage`.

---

## Node Naming Pattern

Node names are derived from the parent cluster name, with two additional components appended:

$$\text{[Cluster Name]}-\text{[ROLE]}-\text{[INDEX]}$$

### 1. ROLE (Node Group/Type)

This defines the primary function of the node within the cluster.

| Value | Description |
| :--- | :--- |
| **cp** | **Control Plane:** Runs master components (etcd, API server, scheduler). |
| **w** | **Worker:** Standard worker node/node pool. |
| **scale** | **Scaled:** Cloud-managed node groups (e.g., AKS/EKS/GKE autoscaled nodes). |

### 2. INDEX (Double-Digit Index)

A sequential, double-digit number for uniqueness within the cluster's role group. **Must be two digits.**

* **Examples:** `01`, `02`, `10`, `15`.

---

## Example Usage

| Resource | Example Name |
| :--- | :--- |
| **Prod AWS Cluster** | `p-aws-web` |
| **Non-Prod Home Cluster** | `np-home-homelab` |
| **Control Plane Node** | `p-aws-web-cp-01` |
| **Worker Node 12** | `np-home-homelab-w-12` |
| **Linode Scaled Node 05** | `dev-lnd-test-scale-05` |