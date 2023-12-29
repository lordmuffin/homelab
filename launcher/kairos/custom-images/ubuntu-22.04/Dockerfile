# Use images from reference/image_matrix/
FROM quay.io/kairos/ubuntu:22.04-standard-amd64-generic-v2.4.3-k3sv1.28.2-k3s1

LABEL org.opencontainers.image.source=https://github.com/lordmuffin/homelab
LABEL org.opencontainers.image.description="My custom kairos ubuntu 22.04 image"
LABEL org.opencontainers.image.licenses=Apache-2.0

RUN sudo apt-get update
RUN sudo apt-get install -y cifs-utils nfs-common open-iscsi lsscsi \
    sg3-utils multipath-tools scsitools

RUN sudo tee /etc/multipath.conf $"<<-'EOF'\
defaults { \n\
    user_friendly_names yes \n\
    find_multipaths yes \n\
} \n\
EOF"

## for apt to be noninteractive
ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN true

## preesed tzdata, update package index, upgrade packages and install needed software
RUN truncate -s0 /tmp/preseed.cfg; \
    echo "tzdata tzdata/Areas select America" >> /tmp/preseed.cfg; \
    echo "tzdata tzdata/Zones/America select Chicago" >> /tmp/preseed.cfg; \
    debconf-set-selections /tmp/preseed.cfg && \
    rm -f /etc/timezone /etc/localtime && \
    apt-get update && \
    apt-get install -y tzdata

## cleanup of files from setup
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
