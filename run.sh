#!/usr/bin/env sh

# Start iptables
# Allow loopback device (internal communication)
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow all local traffic.
iptables -A INPUT -s 172.16.0.1/12 -j ACCEPT
iptables -A OUTPUT -d 172.16.0.1/12 -j ACCEPT

# Allow VPN establishment
iptables -A OUTPUT -p tcp -o eth0 -d tor-proxy --dport 9050 -j ACCEPT
iptables -A INPUT -p tcp -i eth0 -s tor-proxy --sport 9050 -j ACCEPT

# Allow all TUN connections
iptables -A OUTPUT -o tun0 -j ACCEPT
iptables -A INPUT -i tun0 -m state --state RELATED,ESTABLISHED -j ACCEPT

# And drop the rest
iptables -P INPUT DROP
iptables -P OUTPUT DROP
iptables -P FORWARD DROP

cd /opt/vpnwatcher
sleep 60

# Start python
python vpnmanager.py

