import re
import io
from time import sleep
from base64 import b64decode
try:
    from requests import get
except ImportError:
    print("Install bs4")
    exit(1)


class SiteNotPulled(Exception):
    def __init__(self):
        self.code = 1
        self.msg = "Site not pulled"

    def __str__(self):
        return self.msg

class SocksPortNotSet(Exception):
    def __init__(self):
        self.code = 2
        self.msg = "Socks port was not set"
    def __str__(self):
        return self.msg


class VpnConfig:
    def __init__(self, raw):
        self.raw_input = raw
        self.hostname = raw[0]
        self.ip = raw[1]
        self.score = int(raw[2])
        self.ping = raw[3]
        self.speed = int(raw[4])
        self.countrylong = raw[5]
        self.countryshort = raw[6]
        self.numvpnsessions = raw[7]
        self.uptime = raw[8]
        self.totalusers = raw[9]
        self.totaltraffic = raw[10]
        self.logtype = raw[11]
        self.operator = raw[12]
        self.mesasge = raw[13]
        self.vpnconfig = b64decode(raw[14])

    def __str__(self):
        return '{} - {}'.format(self.hostname, self.ip)

    def writeConf(self, path):
        try:
            configpath = path
            f = open(configpath, 'w')
            f.write(self.vpnconfig.decode('UTF-8'))
            f.write('\nkeepalive 10 60')
            f.write('\nresolv-retry infinite')
            f.write('\nsocks-proxy tor-proxy 9050\n')
            f.close()
        except FileNotFoundError:
            print("{} not found. Install openvpn".format(path))

class VpnGate:
    def __init__(self, socks_port=None):
        if socks_port:
            self.socks_port = int(socks_port)
        self.rawsite = None
        self.configlist = []
        self.blacklist = []
        self.currentconfig = None
        self.configs_pulled = 0

    def pullConfigs(self):
        self.configlist = []
        self._httppull()
        self._parse()

    def _httppull(self):
        url = 'https://www.vpngate.net'
        api = '/api/iphone/'
        fullurl = url+api
        user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) '\
                     'Gecko/2009021910 Firefox/3.0.7'
        headers={'User-Agent':user_agent}
        proxy = {"https": 'socks5h://tor-proxy:9050',
                 "http": 'socks5h://tor-proxy:9050'}
        #resp = get(fullurl, proxies=dict(http='socks5://tor:9050'))
        resp = get(fullurl, headers=headers, proxies=proxy)
        if resp.status_code != 200:
            raise SiteNotPulled
        self.rawsite = resp.text.split('\r\n')

    def _parse(self):
        if not self.rawsite:
            raise SiteNotPulled
        for i in self.rawsite:
            vpnline = i.strip().split(',')
            if re.search('^vpn[0-9].*', vpnline[0]):
                config = VpnConfig(vpnline)
                if config.ip in self.blacklist:
                    continue
                self.configlist.append(config)

        self.configlist.sort(key=lambda configlist: configlist.score, reverse=True)

    def get_conf(self):
        if self.currentconfig:
            self.blacklist.append(self.currentconfig.ip)
            self.configs_pulled = self.configs_pulled + 1
        self.currentconfig = self.configlist.pop(0)
        return self.currentconfig


def gatecheck(info):
    if info:
        if info.configs_pulled > 10:
            newgates = VpnGate()
            return newgates
    return None


def main():
    gate = VpnGate()
    try:
        while True:
            try:
                newgates = gatecheck(gate)
                if newgates:
                    print("New Gate")
                    gate = newgates
                config = gate.get_conf()
                print(config)
                config.writeConf(f"{config.ip}.ovpn")
                break
                sleep(1)
            except KeyboardInterrupt:
                break
    except ImportError as e:
        print(e)


if __name__ == "__main__":
    main()
