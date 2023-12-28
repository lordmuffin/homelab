# Use images from reference/image_matrix/
FROM quay.io/kairos/ubuntu:22.04-standard-amd64-generic-v2.4.3-k3sv1.28.2-k3s1

LABEL org.opencontainers.image.source=https://github.com/lordmuffin/homelab
LABEL org.opencontainers.image.description="My custom kairos ubuntu 22.04 image"
LABEL org.opencontainers.image.licenses=Apache-2.0

RUN sudo apt-get update
RUN sudo apt-get install -y cifs-utils nfs-common open-iscsi lsscsi sg3-utils multipath-tools scsitools

RUN sudo tee /etc/multipath.conf $"<<-'EOF'\
defaults { \n\
    user_friendly_names yes \n\
    find_multipaths yes \n\
} \n\
EOF"
