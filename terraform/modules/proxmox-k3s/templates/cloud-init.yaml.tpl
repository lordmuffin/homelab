#cloud-config
hostname: ${hostname}
manage_etc_hosts: true

users:
  - default
  - name: ${username}
    groups:
      - sudo
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ${ssh_keys}

package_update: true
package_upgrade: true

packages:
  - curl
  - wget
  - vim
  - htop
  - net-tools
  - software-properties-common
  - apt-transport-https
  - ca-certificates
  - gnupg
  - lsb-release

runcmd:
  - echo 'Defaults:${username} !requiretty' > /etc/sudoers.d/${username}
  - echo '${username} ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers.d/${username}
  - chmod 440 /etc/sudoers.d/${username}
  - systemctl enable ssh
  - systemctl start ssh
  # Create k3s preparation script
  - |
    cat > /tmp/k3s-prep.sh << 'EOF'
    #!/bin/bash
    
    # Install k3sup
    curl -sLS https://get.k3sup.dev | sh
    sudo install k3sup /usr/local/bin/
    
    # Set up directory for kubeconfig
    mkdir -p /home/${username}/.kube
    chown ${username}:${username} /home/${username}/.kube
    
    # Set hostname properly
    hostnamectl set-hostname ${hostname}
    
    # Update /etc/hosts
    echo "127.0.1.1 ${hostname}" >> /etc/hosts
    
    # Prepare for k3s installation
    echo "Node ${hostname} ready for k3s installation"
    EOF
  - chmod +x /tmp/k3s-prep.sh
  - /tmp/k3s-prep.sh

write_files:
  - path: /etc/systemd/system/k3s-prep.service
    content: |
      [Unit]
      Description=K3s Node Preparation
      After=network-online.target
      Wants=network-online.target
      
      [Service]
      Type=oneshot
      ExecStart=/tmp/k3s-prep.sh
      RemainAfterExit=true
      
      [Install]
      WantedBy=multi-user.target
    permissions: '0644'

  - path: /etc/environment
    content: |
      K3S_VERSION="${k3s_version}"
      K3S_OPTIONS="${k3s_options}"
      VM_TYPE="${vm_type}"
      ENVIRONMENT="${environment}"
      TLS_SAN="${tls_san}"
    append: true

power_state:
  delay: "+1"
  mode: reboot
  message: "Rebooting after cloud-init completion"
  timeout: 30
  condition: True