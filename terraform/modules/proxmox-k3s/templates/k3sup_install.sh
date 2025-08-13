#!/bin/bash

echo "k3sup_install.sh script is running!!!"

# Install k3sup if not already installed
if ! command -v k3sup &> /dev/null; then
    echo "Installing k3sup..."
    curl -sLS https://get.k3sup.dev | sh
    sudo install k3sup /usr/local/bin/
fi

if k3sup --help > /dev/null 2>&1; then
    echo "k3sup installed and ready."
else
    echo "k3sup install FAILED!"
    exit 1
fi

# Parameters
K3SUP_NODE_TYPE=$1
SERVER_IP=$2
NEXT_SERVER_IP=$3
USER=$4
SSH_KEY="$5"
TLS_SAN=$6

SSH_PATH=~/.ssh
SSH_KEY_PATH=~/.ssh/id_rsa

# Set up SSH key
mkdir -p "$SSH_PATH"
echo "$SSH_KEY" > "$SSH_KEY_PATH"
chmod 600 "$SSH_KEY_PATH"

# Get K3s version and options from environment or use defaults
K3S_VERSION="${K3S_VERSION:-v1.28.2+k3s1}"
K3S_OPTIONS="${K3S_OPTIONS:---flannel-backend=none --disable-network-policy} --tls-san=$TLS_SAN"

echo "Node Type: $K3SUP_NODE_TYPE"
echo "Server IP: $SERVER_IP"
echo "Next Server IP: $NEXT_SERVER_IP"
echo "User: $USER"
echo "TLS SAN: $TLS_SAN"

case "$K3SUP_NODE_TYPE" in
    "install")
        echo "Initializing K3s cluster..."
        k3sup install \
            --cluster \
            --ssh-key "$SSH_KEY_PATH" \
            --ip "$SERVER_IP" \
            --user "$USER" \
            --k3s-version "$K3S_VERSION" \
            --no-extras \
            --k3s-extra-args "$K3S_OPTIONS" \
            --local-path ~/.kube/config
        
        if [ $? -eq 0 ]; then
            echo "K3s cluster initialized successfully"
            # Copy kubeconfig for local access
            sudo cp /etc/rancher/k3s/k3s.yaml /home/$USER/.kube/config
            sudo chown $USER:$USER /home/$USER/.kube/config
            chmod 600 /home/$USER/.kube/config
        else
            echo "K3s cluster initialization failed"
            exit 1
        fi
        ;;
        
    "server")
        echo "Adding server node to K3s cluster..."
        k3sup join \
            --server \
            --ssh-key "$SSH_KEY_PATH" \
            --ip "$NEXT_SERVER_IP" \
            --server-ip "$SERVER_IP" \
            --user "$USER" \
            --k3s-version "$K3S_VERSION" \
            --no-extras \
            --k3s-extra-args "$K3S_OPTIONS"
        
        if [ $? -eq 0 ]; then
            echo "Server node joined successfully"
        else
            echo "Server node join failed"
            exit 1
        fi
        ;;
        
    "agent")
        echo "Adding agent node to K3s cluster..."
        k3sup join \
            --ssh-key "$SSH_KEY_PATH" \
            --ip "$NEXT_SERVER_IP" \
            --server-ip "$SERVER_IP" \
            --user "$USER" \
            --k3s-version "$K3S_VERSION"
        
        if [ $? -eq 0 ]; then
            echo "Agent node joined successfully"
        else
            echo "Agent node join failed"
            exit 1
        fi
        ;;
        
    *)
        echo "Invalid node type: $K3SUP_NODE_TYPE"
        echo "Valid types: install, server, agent"
        exit 1
        ;;
esac

echo "k3sup script completed successfully!"