#!/bin/bash
# VM IP Discovery Script for K3s Cluster
# This script discovers the actual IP addresses of VMs from Proxmox API
# and updates the Ansible inventory file

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVENTORY_FILE="$SCRIPT_DIR/../inventory/discovered-hosts.yml"
TEMP_INVENTORY="$SCRIPT_DIR/../inventory/temp-hosts.yml"
TERRAFORM_DIR="/home/lordmuffin/Claude/Git/homelab/infrastructure/proxmox/terraform/environments/production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== K3s VM IP Discovery Script ===${NC}"
echo "Discovering IP addresses for deployed VMs from Proxmox..."

# Function to check if a VM is responsive
check_vm_responsive() {
    local ip=$1
    local timeout=5
    
    # Test SSH connectivity
    timeout $timeout ssh -o ConnectTimeout=$timeout -o StrictHostKeyChecking=no -o BatchMode=yes ubuntu@$ip "echo 'VM responsive'" 2>/dev/null
    return $?
}

# Function to get Proxmox API credentials
get_proxmox_credentials() {
    local node_name=$1
    
    case $node_name in
        "pve2")
            echo "192.168.1.14|terraform@pve!terraform|56a7a10c-51be-4326-9b46-827267a38a42"
            ;;
        "pve-nas-01")
            echo "192.168.1.15|terraform@pve!terraform|74bb1806-b743-459b-bfc1-3734f862030b"
            ;;
        "pve4")
            echo "192.168.1.37|terraform@pve!terraform|b8fa41ff-c4f5-4d05-a805-58d3e60706f3"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Function to get VM IP from Proxmox using API
get_vm_ip_from_proxmox() {
    local proxmox_node=$1
    local vm_id=$2
    local vm_name=$3
    
    # Get API credentials
    local credentials=$(get_proxmox_credentials "$proxmox_node")
    if [[ -z $credentials ]]; then
        echo -e "${RED}Unknown Proxmox node: $proxmox_node${NC}" >&2
        return 1
    fi
    
    IFS='|' read -r proxmox_ip username token <<< "$credentials"
    
    echo -n "Getting IP for VM $vm_name (ID: $vm_id) on $proxmox_node ($proxmox_ip)... " >&2
    
    # Try to get IP using Proxmox API guest agent
    local api_url="https://$proxmox_ip:8006/api2/json"
    local auth_header="Authorization: PVEAPIToken=$username=$token"
    
    # First, try to get network interfaces from guest agent
    local guest_response=$(curl -s -k -H "$auth_header" \
        "$api_url/nodes/$proxmox_node/qemu/$vm_id/agent/network-get-interfaces" 2>/dev/null || echo "")
    
    if [[ -n "$guest_response" && "$guest_response" != *"error"* ]]; then
        # Extract IPv4 address from non-loopback interface
        local ip=$(echo "$guest_response" | jq -r '.data.result[] | select(.name != "lo") | ."ip-addresses"[] | select(."ip-address-type" == "ipv4" and ."ip-address" != "127.0.0.1") | ."ip-address"' 2>/dev/null | head -1)
        
        if [[ -n $ip && $ip != "null" ]]; then
            echo -e "${GREEN}$ip${NC}" >&2
            echo "$ip"  # This goes to stdout for capture
            return 0
        fi
    fi
    
    # Fallback: Get VM config and look for IP in agent info
    echo -e "${YELLOW}guest-agent network failed, trying VM status${NC}" >&2
    
    local vm_status=$(curl -s -k -H "$auth_header" \
        "$api_url/nodes/$proxmox_node/qemu/$vm_id/status/current" 2>/dev/null || echo "")
    
    if [[ -n "$vm_status" && "$vm_status" != *"error"* ]]; then
        # Try to extract IP from agent info in VM status
        local agent_ip=$(echo "$vm_status" | jq -r '.data | if has("agent") then .agent else empty end' 2>/dev/null | grep -oE '192\.168\.[0-9]+\.[0-9]+' | head -1)
        
        if [[ -n $agent_ip ]]; then
            echo -e "${GREEN}$agent_ip (from agent status)${NC}" >&2
            echo "$agent_ip"  # This goes to stdout for capture
            return 0
        fi
    fi
    
    echo -e "${RED}IP not found${NC}" >&2
    return 1
}

# Function to discover VMs from Terraform state and get their IPs from Proxmox
discover_vm_ips() {
    echo -e "${YELLOW}Querying Terraform state for VM information...${NC}"
    
    if [[ ! -f "$TERRAFORM_DIR/terraform.tfstate" ]]; then
        echo -e "${RED}Error: Terraform state not found at $TERRAFORM_DIR${NC}"
        exit 1
    fi
    
    declare -A vm_ips
    
    # Get VM information from Terraform outputs
    local terraform_output=$(cd "$TERRAFORM_DIR" && terraform output -json cluster_nodes 2>/dev/null)
    
    if [[ -z "$terraform_output" || "$terraform_output" == "null" ]]; then
        echo -e "${RED}Error: Could not get cluster nodes from Terraform output${NC}"
        exit 1
    fi
    
    # Parse each VM and get its IP
    echo "$terraform_output" | jq -r 'to_entries[] | "\(.key)|\(.value.vm_id)|\(.value.node_name)|\(.value.name)"' | while IFS='|' read -r terraform_name vm_id proxmox_node vm_name; do
        echo -e "\n${YELLOW}Processing: $vm_name${NC}"
        
        # Get IP from Proxmox
        if ip=$(get_vm_ip_from_proxmox "$proxmox_node" "$vm_id" "$vm_name"); then
            vm_ips[$vm_name]=$ip
            echo "  ✓ $vm_name: $ip"
        else
            echo -e "  ${RED}✗ Failed to get IP for $vm_name${NC}"
        fi
    done
    
    # Create a file to store the discovered IPs for the update function
    > "$SCRIPT_DIR/discovered_ips.tmp"
    echo "$terraform_output" | jq -r 'to_entries[] | "\(.key)|\(.value.vm_id)|\(.value.node_name)|\(.value.name)"' | while IFS='|' read -r terraform_name vm_id proxmox_node vm_name; do
        if ip=$(get_vm_ip_from_proxmox "$proxmox_node" "$vm_id" "$vm_name"); then
            echo "$vm_name|$ip" >> "$SCRIPT_DIR/discovered_ips.tmp"
        fi
    done
    
    # Display discovered VMs
    echo -e "\n${GREEN}Discovered K3s VMs:${NC}"
    if [[ -f "$SCRIPT_DIR/discovered_ips.tmp" ]]; then
        while IFS='|' read -r vm_name ip; do
            echo "  $vm_name: $ip"
        done < "$SCRIPT_DIR/discovered_ips.tmp"
        
        # Update inventory file
        echo -e "\n${YELLOW}Updating inventory file...${NC}"
        update_inventory_with_discovered_ips
    else
        echo -e "${RED}No VMs discovered${NC}"
    fi
}

# Function to update inventory file with discovered IPs
update_inventory_with_discovered_ips() {
    if [[ ! -f $INVENTORY_FILE ]]; then
        echo -e "${RED}Error: Inventory file not found at $INVENTORY_FILE${NC}"
        exit 1
    fi
    
    if [[ ! -f "$SCRIPT_DIR/discovered_ips.tmp" ]]; then
        echo -e "${RED}Error: No discovered IPs file found${NC}"
        exit 1
    fi
    
    # Copy original inventory to temp file
    cp "$INVENTORY_FILE" "$TEMP_INVENTORY"
    
    # Update IPs in the temp file
    while IFS='|' read -r vm_name ip; do
        echo "Updating $vm_name with IP $ip"
        
        # Replace any existing IP with actual IP for this VM using more flexible pattern
        sed -i "/# VM: $vm_name/,+1 s/ansible_host: \"[^\"]*\"/ansible_host: \"$ip\"/" "$TEMP_INVENTORY"
    done < "$SCRIPT_DIR/discovered_ips.tmp"
    
    # Count how many IPs were updated
    total_discovered=$(wc -l < "$SCRIPT_DIR/discovered_ips.tmp" 2>/dev/null || echo "0")
    
    if [[ $total_discovered -gt 0 ]]; then
        echo -e "${GREEN}Updated $total_discovered VMs! Replacing inventory file.${NC}"
        mv "$TEMP_INVENTORY" "$INVENTORY_FILE"
    else
        echo -e "${YELLOW}Warning: No VMs were updated.${NC}"
        echo "Updated inventory saved as: $TEMP_INVENTORY"
        echo "Review and manually move to $INVENTORY_FILE when ready."
    fi
    
    # Cleanup temporary file
    rm -f "$SCRIPT_DIR/discovered_ips.tmp"
}

# Function to test SSH connectivity to all discovered VMs
test_ssh_connectivity() {
    echo -e "\n${YELLOW}Testing SSH connectivity to all VMs...${NC}"
    
    local success_count=0
    local total_count=0
    
    while IFS= read -r line; do
        if [[ $line =~ ansible_host:\ \"([0-9.]+)\" ]]; then
            local ip="${BASH_REMATCH[1]}"
            if [[ $ip != "TBD_DISCOVER" ]]; then
                total_count=$((total_count + 1))
                echo -n "Testing SSH to $ip... "
                
                if check_vm_responsive $ip; then
                    echo -e "${GREEN}SUCCESS${NC}"
                    success_count=$((success_count + 1))
                else
                    echo -e "${RED}FAILED${NC}"
                fi
            fi
        fi
    done < "$INVENTORY_FILE"
    
    echo -e "\nSSH Connectivity Results: ${GREEN}$success_count${NC}/$total_count VMs responsive"
    
    if [[ $success_count -eq $total_count && $total_count -gt 0 ]]; then
        echo -e "${GREEN}✅ All VMs are SSH accessible!${NC}"
        return 0
    else
        echo -e "${RED}❌ Some VMs are not accessible.${NC}"
        return 1
    fi
}

# Function to use manual IP mapping
use_manual_mapping() {
    local mapping_file="$SCRIPT_DIR/manual-ip-mapping.txt"
    
    if [[ ! -f "$mapping_file" ]]; then
        echo -e "${RED}Error: Manual IP mapping file not found at $mapping_file${NC}"
        echo "Create the file and add VM IPs in format: vm_name|ip_address"
        exit 1
    fi
    
    echo -e "${YELLOW}Using manual IP mapping from $mapping_file${NC}"
    
    # Check for incomplete mappings
    if grep -q "XXX" "$mapping_file"; then
        echo -e "${RED}Error: Manual mapping file contains placeholder 'XXX' entries${NC}"
        echo "Please edit $mapping_file and replace all 'XXX' with actual IP addresses"
        exit 1
    fi
    
    # Copy valid mappings to temporary file
    grep -v "^#" "$mapping_file" | grep -v "^$" > "$SCRIPT_DIR/discovered_ips.tmp"
    
    if [[ ! -s "$SCRIPT_DIR/discovered_ips.tmp" ]]; then
        echo -e "${RED}Error: No valid IP mappings found${NC}"
        exit 1
    fi
    
    echo -e "\n${GREEN}Manual IP Mappings:${NC}"
    while IFS='|' read -r vm_name ip; do
        echo "  $vm_name: $ip"
    done < "$SCRIPT_DIR/discovered_ips.tmp"
    
    echo -e "\n${YELLOW}Updating inventory file...${NC}"
    update_inventory_with_discovered_ips
}

# Main execution
main() {
    case "${1:-discover}" in
        "discover")
            discover_vm_ips
            ;;
        "manual")
            use_manual_mapping
            ;;
        "test")
            test_ssh_connectivity
            ;;
        "both")
            discover_vm_ips
            echo ""
            test_ssh_connectivity
            ;;
        "manual-test")
            use_manual_mapping
            echo ""
            test_ssh_connectivity
            ;;
        *)
            echo "Usage: $0 [discover|manual|test|both|manual-test]"
            echo "  discover:     Query Proxmox for K3s VM IPs and update inventory"
            echo "  manual:       Use manual IP mapping file to update inventory"
            echo "  test:         Test SSH connectivity to VMs in inventory"
            echo "  both:         Discover IPs and test connectivity"
            echo "  manual-test:  Use manual mapping and test connectivity"
            echo ""
            echo "For manual mapping, edit: $SCRIPT_DIR/manual-ip-mapping.txt"
            exit 1
            ;;
    esac
}

main "$@"