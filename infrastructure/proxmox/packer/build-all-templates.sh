#!/bin/bash
# Build Ubuntu K3s templates on all Proxmox nodes
# This script builds templates on each node to avoid cross-node dependencies

set -e

# Parse command line arguments
FORCE_REBUILD=false
DRY_RUN=false
for arg in "$@"; do
    case $arg in
        --force|-f)
            FORCE_REBUILD=true
            shift
            ;;
        --dry-run|-n)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--force|-f] [--dry-run|-n] [--help|-h]"
            echo "  --force, -f     Force rebuild even if template already exists"
            echo "  --dry-run, -n   Show what would be done without building"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🚀 Building Ubuntu K3s templates on all Proxmox nodes"
echo "=================================================="
if [ "$DRY_RUN" = true ]; then
    echo "👁️  Dry run mode: Will show what would be done without building"
fi
if [ "$FORCE_REBUILD" = true ]; then
    echo "🔄 Force rebuild mode: Will rebuild existing templates"
fi
if [ "$DRY_RUN" = true ] || [ "$FORCE_REBUILD" = true ]; then
    echo ""
fi

# Array of node configurations with suggested VM IDs
# Format: "node:vm_id" or just "node" for auto-assigned ID
declare -A NODE_CONFIGS=(
    ["pve2"]="9000"
    ["pve-nas-01"]="9001"
    ["pve4"]="9002"
)
BUILD_SUCCESS=0
BUILD_FAILED=0
BUILD_SKIPPED=0

# Function to check if VM ID already exists on Proxmox node
check_vm_exists() {
    local vm_id=$1
    local api_url=$2
    local api_token=$3
    
    if [ -z "$vm_id" ] || [ -z "$api_url" ] || [ -z "$api_token" ]; then
        echo "⚠️  Cannot check VM existence - missing parameters"
        return 1
    fi
    
    # Extract base URL and build the VM check endpoint
    local base_url="${api_url%/api2/json}"
    local check_url="${base_url}/api2/json/nodes/${PROXMOX_NODE}/qemu/${vm_id}/status/current"
    
    # Check if VM exists using Proxmox API
    local response=$(curl -k -s --connect-timeout 10 \
        -H "Authorization: PVEAPIToken=${api_token}" \
        "${check_url}" 2>/dev/null)
    
    # Check if the response contains actual VM data (not null or error)
    if echo "$response" | grep -q '"data":{' && ! echo "$response" | grep -q '"data":null'; then
        return 0  # VM exists
    else
        return 1  # VM doesn't exist or error
    fi
}

# Function to build template on a specific node
build_node_template() {
    local node=$1
    local vm_id=${NODE_CONFIGS[$node]}
    local env_file=".env.${node}"
    
    echo ""
    echo "🔧 Processing node: ${node}"
    echo "📄 Environment file: ${env_file}"
    echo "🆔 Template VM ID: ${vm_id:-auto-assigned}"
    
    # Check if environment file exists
    if [ ! -f "${env_file}" ]; then
        echo "❌ Environment file ${env_file} not found!"
        echo "   Please copy .env.${node}.example to ${env_file} and configure it"
        return 1
    fi
    
    # Source environment variables
    source "${env_file}"
    
    # Validate required variables
    if [ -z "$PROXMOX_URL" ] || [ -z "$PROXMOX_NODE" ] || [ -z "$PROXMOX_USERNAME" ]; then
        echo "❌ Missing required environment variables in ${env_file}"
        echo "   Please check PROXMOX_URL, PROXMOX_NODE, and PROXMOX_USERNAME"
        return 1
    fi
    
    # Prepare API token for authentication
    local api_token="${PROXMOX_USERNAME}=${PROXMOX_TOKEN}"
    
    # Test connection first  
    echo "🔍 Testing connection to ${PROXMOX_URL}..."
    local base_url="${PROXMOX_URL%/api2/json}"
    if ! timeout 10 curl -k -s --connect-timeout 5 "${base_url}" > /dev/null 2>&1; then
        echo "❌ Cannot connect to Proxmox server at ${base_url}"
        echo "   Please check your network connection and API URL"
        return 1
    fi
    echo "✅ Connection successful"
    
    # Check if template with specified VM ID already exists (unless force rebuild)
    if [ -n "$vm_id" ] && [ "$FORCE_REBUILD" = false ]; then
        echo "🔍 Checking if template VM ID $vm_id already exists..."
        if check_vm_exists "$vm_id" "$PROXMOX_URL" "$api_token"; then
            echo "⏭️  Template with VM ID $vm_id already exists on $node - skipping build"
            echo "   (Use --force to rebuild existing templates)"
            return 2  # Special return code for "skipped"
        else
            echo "✅ VM ID $vm_id is available - proceeding with build"
        fi
    elif [ -n "$vm_id" ] && [ "$FORCE_REBUILD" = true ]; then
        echo "🔄 Force rebuild mode: Will overwrite existing template VM ID $vm_id if present"
    fi
    
    # Build template - export variables for Packer env() function
    echo "🏗️  Building template..."
    export PROXMOX_URL PROXMOX_USERNAME PROXMOX_TOKEN PROXMOX_NODE
    
    # Build command with optional VM ID
    local build_cmd="packer build"
    if [ -n "$vm_id" ]; then
        build_cmd="$build_cmd -var template_vm_id=$vm_id"
    fi
    build_cmd="$build_cmd ubuntu-k3s.pkr.hcl"
    
    if [ "$DRY_RUN" = true ]; then
        echo "👁️  [DRY RUN] Would execute: $build_cmd"
        echo "✅ Template build simulated successfully on ${node}"
        return 0
    else
        echo "▶️  Executing: $build_cmd"
        if eval $build_cmd; then
            echo "✅ Template built successfully on ${node}"
            return 0
        else
            echo "❌ Template build failed on ${node}"
            return 1
        fi
    fi
}

# Build templates on all nodes
for node in "${!NODE_CONFIGS[@]}"; do
    set +e  # Temporarily disable exit on error
    build_node_template "$node"
    exit_code=$?
    set -e  # Re-enable exit on error
    
    if [ $exit_code -eq 0 ]; then
        BUILD_SUCCESS=$((BUILD_SUCCESS + 1))
    elif [ $exit_code -eq 2 ]; then
        BUILD_SKIPPED=$((BUILD_SKIPPED + 1))
    else
        BUILD_FAILED=$((BUILD_FAILED + 1))
        echo "⚠️  Continuing with next node..."
    fi
done

echo ""
echo "📊 Build Summary"
echo "================"
echo "✅ Successful builds: ${BUILD_SUCCESS}"
echo "⏭️  Skipped builds: ${BUILD_SKIPPED}"
echo "❌ Failed builds: ${BUILD_FAILED}"
echo "📋 Total nodes: ${#NODE_CONFIGS[@]}"

if [ $BUILD_FAILED -eq 0 ]; then
    if [ $BUILD_SKIPPED -gt 0 ] && [ $BUILD_SUCCESS -eq 0 ]; then
        echo "⏭️  All templates already exist - no builds needed"
    elif [ $BUILD_SKIPPED -gt 0 ]; then
        echo "🎉 All operations completed! (Built: ${BUILD_SUCCESS}, Skipped: ${BUILD_SKIPPED})"
    else
        echo "🎉 All templates built successfully!"
    fi
    exit 0
elif [ $((BUILD_SUCCESS + BUILD_SKIPPED)) -gt 0 ]; then
    echo "⚠️  Mixed results: Built ${BUILD_SUCCESS}, Skipped ${BUILD_SKIPPED}, Failed ${BUILD_FAILED}"
    echo "   Check the logs above for details on failed builds"
    exit 1
else
    echo "💥 All template builds failed"
    echo "   Please check your configuration and network connectivity"
    exit 1
fi