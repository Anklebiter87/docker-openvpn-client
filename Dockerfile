FROM archlinux
LABEL maintainer="anklebiter87@gmail.com"

# Add openvpn
RUN pacman -Syuq --noconfirm && \
    pacman -S --noconfirm openvpn iptables python python-pip python-pysocks python-requests python-pexpect && \
    pacman -Scc --noconfirm && \
    rm -rf /var/lib/pacman/sync/*

# Create the volume to read vpn config
VOLUME "/etc/openvpn"

COPY run.sh /usr/bin
RUN mkdir /opt/vpnwatcher/
COPY *.py /opt/vpnwatcher/

# Give run the execute flag
RUN chmod 755 /usr/bin/run.sh

ENTRYPOINT /usr/bin/run.sh
