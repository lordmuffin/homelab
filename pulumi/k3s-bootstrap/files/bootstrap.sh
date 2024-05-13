#!/bin/sh

echo "bootstrap.sh script is running!!!"

# Install k3sup
curl -sLS https://get.k3sup.dev | sh
sudo install k3sup /usr/local/bin/

k3sup --help