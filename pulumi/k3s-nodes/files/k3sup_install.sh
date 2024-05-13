#!/bin/sh

echo "bootstrap.sh script is running!!!"

# Install k3sup
curl -sLS https://get.k3sup.dev | sh
sudo install k3sup /usr/local/bin/

if k3sup --help ; then
  echo "k3sup installed."
else
  echo "k3sup install FAILED!"
  exit 1
fi

K3S_VERSION="v1.22.4+k3s1"
K3S_OPTIONS="--flannel-backend=none --tls-san=192.168.10.10"
K3SUP_NODE_TYPE=$1
SERVER_IP=$2
NEXT_SERVER_IP=$3
USER=$4
SSH_KEY=$5
SSH_PATH=~/.ssh
SSH_KEY_PATH=~/.ssh/id_rsa

if $(ls $SSH_PATH) ; then
  echo ".ssh exists"
else
  mdkir $SSH_PATH
  echo ".ssh did not exist, but I created it"
fi
echo "$SSH_KEY" > "$SSH_KEY_PATH"
ssh-add $SSH_KEY_PATH

echo "Var K3SUP_NODE_TYPE=$K3SUP_NODE_TYPE"
echo "Var SERVER_IP=$SERVER_IP"
echo "Var NEXT_SERVER_IP=$NEXT_SERVER_IP"
echo "Var USER=$USER"
echo "Var SSH_KEY=$SSH_KEY"

echo "k3sup init cluster"
if [ "$K3SUP_NODE_TYPE" = 'install' ]; then
  k3sup install --cluster --ssh-key $SSH_KEY_PATH --ip $SERVER_IP --user $USER --k3s-version $K3S_VERSION --no-extras --k3s-extra-args $K3S_OPTIONS
fi;

echo "k3sup add server nodes"
if [ "$K3SUP_NODE_TYPE" = 'server' ]; then
  k3sup join --server --ssh-key $SSH_KEY_PATH --ip $NEXT_SERVER_IP --server $SERVER_IP --user $USER --k3s-version $K3S_VERSION --no-extras --k3s-extra-args $K3S_OPTIONS
fi;

echo "k3sup add agent nodes"
if [ "$K3SUP_NODE_TYPE" = 'agent' ]; then
  k3sup join --ssh-key $SSH_KEY_PATH --ip $NEXT_SERVER_IP --server $SERVER_IP --user $USER --k3s-version $K3S_VERSION --no-extras --k3s-extra-args $K3S_OPTIONS
fi;

echo "k3sup script complete!!!"