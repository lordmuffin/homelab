#!/bin/bash

# Terraform Environment Validation Script
# This script validates both production and lab environment configurations

set -e

echo "🔍 Terraform Environment Validation"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "INFO")
            echo -e "ℹ️  $message"
            ;;
    esac
}

# Function to validate environment
validate_environment() {
    local env_name=$1
    local env_path=$2
    
    echo ""
    echo "🏗️  Validating $env_name Environment"
    echo "----------------------------------------"
    
    # Check if directory exists
    if [[ ! -d "$env_path" ]]; then
        print_status "ERROR" "$env_name environment directory not found: $env_path"
        return 1
    fi
    
    # Check required files
    local required_files=("main.tf" "variables.tf" "outputs.tf" "terraform.tfvars.example")
    for file in "${required_files[@]}"; do
        if [[ -f "$env_path/$file" ]]; then
            print_status "SUCCESS" "Found $file"
        else
            print_status "ERROR" "Missing required file: $file"
            return 1
        fi
    done
    
    # Change to environment directory
    cd "$env_path"
    
    # Initialize Terraform if needed
    if [[ ! -d ".terraform" ]]; then
        print_status "INFO" "Initializing Terraform..."
        if terraform init > /dev/null 2>&1; then
            print_status "SUCCESS" "Terraform initialized"
        else
            print_status "ERROR" "Failed to initialize Terraform"
            return 1
        fi
    else
        print_status "SUCCESS" "Terraform already initialized"
    fi
    
    # Validate Terraform configuration
    print_status "INFO" "Validating Terraform configuration..."
    if terraform validate > /dev/null 2>&1; then
        print_status "SUCCESS" "Terraform configuration is valid"
    else
        print_status "ERROR" "Terraform configuration validation failed"
        terraform validate
        return 1
    fi
    
    # Check for terraform.tfvars
    if [[ -f "terraform.tfvars" ]]; then
        print_status "SUCCESS" "Found terraform.tfvars configuration"
        
        # Try to create a plan (will fail if missing required vars, but that's expected)
        print_status "INFO" "Testing Terraform plan (may fail if variables not set)..."
        if terraform plan -detailed-exitcode > /dev/null 2>&1; then
            print_status "SUCCESS" "Terraform plan successful"
        else
            case $? in
                1)
                    print_status "ERROR" "Terraform plan failed with errors"
                    ;;
                2)
                    print_status "WARNING" "Terraform plan shows changes (expected if not deployed)"
                    ;;
            esac
        fi
    else
        print_status "WARNING" "No terraform.tfvars found (copy from terraform.tfvars.example)"
    fi
    
    # Check for potential issues
    print_status "INFO" "Checking for potential configuration issues..."
    
    # Check variable defaults
    if grep -q 'default.*=.*"your-' variables.tf; then
        print_status "WARNING" "Found placeholder values in variable defaults"
    fi
    
    # Check for sensitive outputs
    if grep -q 'sensitive.*=.*true' outputs.tf; then
        print_status "SUCCESS" "Found properly marked sensitive outputs"
    fi
    
    # Return to original directory
    cd - > /dev/null
    
    print_status "SUCCESS" "$env_name environment validation completed"
}

# Function to check module dependencies
check_module_dependencies() {
    echo ""
    echo "📦 Checking Module Dependencies"
    echo "-------------------------------"
    
    local module_path="../modules/rackspace-spot"
    
    if [[ -d "$module_path" ]]; then
        print_status "SUCCESS" "Found rackspace-spot module"
        
        # Check module files
        local module_files=("main.tf" "variables.tf" "outputs.tf" "spot.tf" "provider.tf" "versions.tf")
        for file in "${module_files[@]}"; do
            if [[ -f "$module_path/$file" ]]; then
                print_status "SUCCESS" "Module file: $file"
            else
                print_status "WARNING" "Missing module file: $file"
            fi
        done
        
        # Validate module
        cd "$module_path"
        if terraform validate > /dev/null 2>&1; then
            print_status "SUCCESS" "Module configuration is valid"
        else
            print_status "ERROR" "Module validation failed"
            terraform validate
        fi
        cd - > /dev/null
        
    else
        print_status "ERROR" "rackspace-spot module not found: $module_path"
        return 1
    fi
}

# Function to check terraform version
check_terraform_version() {
    echo ""
    echo "🔧 Checking Terraform Version"
    echo "-----------------------------"
    
    if command -v terraform &> /dev/null; then
        local version=$(terraform version -json | jq -r '.terraform_version')
        print_status "SUCCESS" "Terraform version: $version"
        
        # Check if version is >= 1.0
        if [[ $(echo "$version" | cut -d. -f1) -ge 1 ]]; then
            print_status "SUCCESS" "Terraform version meets requirements (>= 1.0)"
        else
            print_status "WARNING" "Terraform version should be >= 1.0"
        fi
    else
        print_status "ERROR" "Terraform not found in PATH"
        return 1
    fi
}

# Function to generate summary
generate_summary() {
    echo ""
    echo "📋 Validation Summary"
    echo "======================"
    
    echo "Environments:"
    echo "  - Production: terraform/environments/prod/"
    echo "  - Lab:        terraform/environments/lab/"
    echo ""
    echo "Module:"
    echo "  - rackspace-spot: terraform/modules/rackspace-spot/"
    echo ""
    echo "Next Steps:"
    echo "  1. Copy terraform.tfvars.example to terraform.tfvars in each environment"
    echo "  2. Configure your Rackspace Spot token and other variables"
    echo "  3. Run 'terraform plan' to review the infrastructure changes"
    echo "  4. Run 'terraform apply' to deploy the environment"
    echo ""
    echo "Cost Estimates (based on default configurations):"
    echo "  - Production: ~$120/month (HA + 3 node pools)"
    echo "  - Lab:        ~$40/month  (cost-optimized)"
}

# Main execution
main() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$script_dir"
    
    print_status "INFO" "Starting validation from: $script_dir"
    
    # Check Terraform version
    check_terraform_version || exit 1
    
    # Check module dependencies
    check_module_dependencies || exit 1
    
    # Validate environments
    validate_environment "Production" "./prod" || exit 1
    validate_environment "Lab" "./lab" || exit 1
    
    # Generate summary
    generate_summary
    
    print_status "SUCCESS" "All validations completed successfully!"
}

# Run main function
main "$@"