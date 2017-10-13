FROM alpine
LABEL maintainer="anklebiter87@gmail.com"

# Add openvpn
RUN apk update && apk add bash openvpn iptables

# Create the volume to read vpn config
VOLUME "/etc/openvpn"

COPY run.sh /usr/sbin

# Give run the execute flag
RUN chmod 755 /usr/sbin/run.sh


ENTRYPOINT /usr/sbin/run.sh
