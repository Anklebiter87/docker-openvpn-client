#!/usr/bin/env python

import time
import pexpect
from os import remove
from json import loads
from requests import get
from os.path import exists
from datetime import datetime
from gatepuller import VpnGate


class SiteNotPulled(Exception):
    def __init__(self):
        self.code = 1
        self.msg = "Site not pulled"

    def __str__(self):
        return self.msg


class AuthFailed(Exception):
    def __init__(self):
        self.code = 2
        self.mesg = "Failed to authenticate"

    def __str__(self):
        return self.mesg


class TimedOut(Exception):
    def __init__(self):
        self.code = 3
        self.mesg = "failed to connect"

    def __str__(self):
        return self.mesg


class VpnManager:
    def __init__(self):
        self.vpnconfigs = []
        self.configPath = None
        self.vpnStarted = False
        self.torChecked = False
        self.session = None
        self.vpnGate = VpnGate()
        self.failedVpnCheckCount = 0
        self.maxPulledConfigs = 15

    def checkTor(self):
        url = 'https://check.torproject.org/api/ip'
        try:
            ret = self._request_get(url)
            if ret['IsTor']:
                print(f"{datetime.now()}: Tor is working and our IP is {ret['IP']}")
                self.torChecked = True
        except SiteNotPulled as e:
            print(e.msg)
            print("Failed to pull tor check site")
            self.torChecked = False

        return self.torChecked

    def vpnCheck(self):
        if not self.vpnStarted:
            return False
        url = "https://ifconfig.me/all.json"
        try:
            ret = self._request_get(url, useProxy=False)
            if ret['ip_addr'] == self.vpnGate.currentconfig.ip:
                self.vpnStarted = True
                print(f"{datetime.now()}: Vpn is working and our IP is {ret['ip_addr']}")
                self.failedVpnCheckCount = 0
            else:
                print(f"{datetime.now()}: Vpn is not working. Current IP is {ret['ip_addr']} expected {self.vpnGate.currentconfig.ip}")
                if(self.failedVpnCheckCount > 3):
                    print(f"{datetime.now()}: Vpn check failed too many times, killing vpn")
                    self.killVpn()
                self.failedVpnCheckCount = self.failedVpnCheckCount + 1
        except SiteNotPulled:
            print(f"{datetime.now()}: Failed to pull vpn check site")
            if(self.failedVpnCheckCount > 3):
                self.killVpn()
            self.failedVpnCheckCount = self.failedVpnCheckCount + 1
        return self.vpnStarted

    def _request_get(self, fullurl, useProxy=True):
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.10 Safari/605.1.1'
        headers={'User-Agent':user_agent}
        proxy = None
        if(useProxy):
            proxy = {"https": 'socks5h://tor-proxy:9050',
                     "http": 'socks5h://tor-proxy:9050'}

        try:
            resp = get(fullurl, headers=headers, proxies=proxy, timeout=30)
            if resp.status_code != 200:
                raise SiteNotPulled
            return loads(resp.text)
        except Exception as e:
            print(f"{datetime.now()}: Exception occurred while making request: {e}")
            raise SiteNotPulled

    def pullConfig(self):
        if(self.torChecked):
            if(not self.vpnGate.configlist):
                self.vpnGate.pullConfigs()
            elif self.vpnGate.configs_pulled > self.maxPulledConfigs:
                self.vpnGate.pullConfigs()

    def configExists(self):
        if self.configPath and exists(self.configPath):
            return True
        return False

    def configCount(self):
        return len(self.vpnGate.configlist)

    def writeConfig(self):
        config = self.vpnGate.get_conf()
        if(self.configPath and exists(self.configPath)):
            print(f"{datetime.now()}: Removing old config {self.configPath}")
            remove(self.configPath)
        if(config.ip not in self.vpnconfigs):
            self.configPath = f"{config.ip}.ovpn"
            config.writeConf(self.configPath)
            self.vpnconfigs.append(config.ip)
            print(f"{datetime.now()}: Config {self.configPath} written")

    def startVpn(self):
        pattern = ['Initialization Sequence Completed',
                   'AUTH_FAILED',
                   'Connection timed out',
                   pexpect.EOF,
                   pexpect.TIMEOUT]
        cmd = f'openvpn --data-ciphers DEFAULT:AES-128-CBC --config {self.configPath}'
        if not self.vpnStarted:
            print(f"{datetime.now()}: Starting vpn with config {self.configPath}")
            self.session = pexpect.spawn(cmd)
            code = self.session.expect(pattern)
            if code == 0:
                print(f"{datetime.now()}: Vpn started successfully")
                self.vpnStarted = True
                return self.vpnStarted
            elif code == 1:
                print(f"{datetime.now()}: Vpn failed to authenticate")
                self.killVpn()
                raise AuthFailed
            elif code == 2:
                print(f"{datetime.now()}: Vpn connection timed out")
                self.killVpn()
                raise TimedOut
            elif code > len(pattern) - 2:
                print(f"{datetime.now()}: Vpn connection failed with unexpected error")
                self.killVpn()
                raise TimedOut

    def killVpn(self):
        if self.session:
            self.session.close()
            self.vpnStarted = False
            self.session = None

def killVpn(manager):
    manager.killVpn()

def main():
    vpnRotate = "/tmp/vpnrotate.lock"
    manager = VpnManager()
    try:
        while True:
            if(manager.checkTor()):
                manager.pullConfig()
            else:
                print(f"{datetime.now()}: Tor needs to be restarted")
                continue

            if(manager.configCount() > 0 and not manager.vpnStarted):
                manager.writeConfig()

            if(manager.configExists()):
                if not manager.vpnStarted:
                    try:
                        manager.startVpn()
                    except AuthFailed:
                        print(f"{datetime.now()}: Auth Failed")
                        manager.killVpn()
                    except TimedOut:
                        print(f"{datetime.now()}: Timed Out")
                        manager.killVpn()
                else:
                    if not manager.vpnCheck():
                        manager.killVpn()
                    else:
                        if(exists(vpnRotate)):
                            print(f"{datetime.now()}: Vpn rotate lock found, killing vpn")
                            manager.killVpn()
                            remove(vpnRotate)
            time.sleep(10)
    except KeyboardInterrupt:
        print(f"{datetime.now()}: Exiting")
        manager.killVpn()


if __name__ == "__main__":
    main()