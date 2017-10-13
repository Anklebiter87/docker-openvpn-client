FROM alpine
LABEL maintainer="anklebiter87@gmail.com"

# Add openvpn
RUN apk update && apk add openvpn iptables

# Create the volume to read vpn config
VOLUME "/etc/openvpn"

COPY run.sh /usr/sbin

# Give run the execute flag
RUN chmod 755 /usr/sbin/run.sh

ENTRYPOINT /bin/sh
