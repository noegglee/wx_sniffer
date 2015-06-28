# -*- coding: utf-8 -*-

__author__ = 'nekocode'
import os
import os.path
import httplib2
import json
import time
import zipfile
from ctypes import *
from winpcapy import *
import StringIO
import dpkt
import thread
import urlparse
from threading import Thread


class WxSniffer(Thread):
    __send_headers = {
        'Host': 'mp.weixin.qq.com',
        'User-Agent':
            'Mozilla/5.0 (Linux; U; Android 4.4.4; zh-cn; MI 3W Build/KTU84P) '
            'AppleWebKit/533.1 (KHTML, like Gecko)Version/4.0 MQQBrowser/5.4 TBS/025411 '
            'Mobile Safari/533.1 MicroMessenger/6.1.0.73_r1097298.543 NetType/WIFI',
        'Accept': 'text/xml, text/html, application/xhtml+xml, image/png, text/plain, */*;q=0.8',
        'Accept-Charset': 'utf-8, iso-8859-1, utf-16, *;q=0.7',
        'Accept-Encoding': 'gzip',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest'
    }

    __uin = 'MTkzMjY4MDUxNA%3D%3D'
    __key = 'c468684b929d2be2745898b4bc6a82fffe1638ec75ef8fa872dcbc6079ab41ec99151dba3caf92c2a01322534a3ec72b'
    __scopit = '\simulate.py '

    PHAND = CFUNCTYPE(None, POINTER(c_ubyte), POINTER(pcap_pkthdr), POINTER(c_ubyte))
    LINE_LEN = 16

    def simulate_open_wxarticle(self, emulator_id):
        os.system('monkeyrunner ' + os.getcwd() + self.__scopit + str(emulator_id))

    def get_wxarticle_state(self, url):
        query = urlparse.urlparse(url).query
        params = urlparse.parse_qs(query)
        __biz = params["__biz"][0]
        mid = params["mid"][0]
        sn = params["sn"][0]
        idx = params["idx"][0]
        url = 'http://mp.weixin.qq.com/mp/getappmsgext'
        url += '?' + '__biz=' + __biz + '&mid=' + mid + '&sn=' + sn + '&idx=' + idx + '&devicetype=android-10&version=&f=json'
        url += '&uin=' + self.__uin + '&key=' + self.__key
        __http = httplib2.Http()
        response, content = __http.request(url, 'GET', headers=self.__send_headers)
        # content = content.decode('utf-8', 'replace').encode(sys.getfilesystemencoding())
        try:
            rlt_json = json.loads(content)
            _rlt = rlt_json['appmsgstat']['read_num'], rlt_json['appmsgstat']['like_num']
        except Exception:
            _rlt = None
            # self.simulate_open_wxarticle(1)
        return _rlt

    def on_key_getted(self):
        print 'uin: ' + self.__uin
        print 'key: ' + self.__key

    def run(self):
        def _packet_handler(param, header, pkt_data):
            raw_data = string_at(pkt_data, header.contents.len)
            p = dpkt.ethernet.Ethernet(raw_data)
            if p.data.data.__class__.__name__ == 'TCP':
                tcp_data = p.data.data
                if tcp_data.dport == 80:
                    if "/getappmsgext" in tcp_data.data:
                        # print tcp_data.data
                        h = dpkt.http.Request(tcp_data.data + "\n  ")
                        http_header = h.headers
                        url = "http://" + http_header['host'] + h.uri
                        query = urlparse.urlparse(url).query
                        params = urlparse.parse_qs(query)
                        self.__uin = params['uin'][0]
                        self.__key = params['key'][0]
                        self.on_key_getted()

        packet_handler = self.PHAND(_packet_handler)
        alldevs = POINTER(pcap_if_t)()
        errbuf = create_string_buffer(PCAP_ERRBUF_SIZE)

        # Retrieve the device list
        if pcap_findalldevs(byref(alldevs), errbuf) == -1:
            print ("Error in pcap_findalldevs: %s\n" % errbuf.value)
            sys.exit(1)
        try:
            d = alldevs.contents
        except:
            print ("Error in pcap_findalldevs: %s" % errbuf.value)
            print ("Maybe you need admin privilege?\n")
            sys.exit(1)
        adhandle = pcap_open_live(d.name, 65536, 1, 0, errbuf)
        if not adhandle:
            print("\nUnable to open the adapter. %s is not supported by Pcap-WinPcap\n" % d.contents.name)
            pcap_freealldevs(alldevs)
            sys.exit(-1)
        pcap_freealldevs(alldevs)
        fcode = bpf_program()
        netmask = 0xffffff
        filter_str = "ip and tcp and dst host mp.weixin.qq.com and dst port 80"
        # compile the filter
        if pcap_compile(adhandle, byref(fcode), filter_str, 1, netmask) < 0:
            print('\nError compiling filter: wrong syntax.\n')
            pcap_close(adhandle)
            sys.exit(-3)
        # set the filter
        if pcap_setfilter(adhandle, byref(fcode)) < 0:
            print('\nError setting the filter\n')
            pcap_close(adhandle)
            sys.exit(-4)
        pcap_loop(adhandle, -1, packet_handler, None)
        pcap_close(adhandle)
        thread.exit_thread()


# Fiddler抓包文件分析
# def getkey():
#     nowdir = os.getcwd()
#     nowidr_files = os.listdir(nowdir)
#     sazfiles = filter(lambda x: x[-4:] == '.saz', nowidr_files)
#     sazfiles.sort()
#     if 'tmp' in nowidr_files:
#         os.system('rmdir /s /q tmp')
#     # os.system('unzip -d tmp ' + files[-1])
#     if sazfiles:
#         z = zipfile.ZipFile(sazfiles[-1], mode='r')
#         zipfiles = filter(lambda x: (len(x) > 6 and x[-6:] == '_c.txt'), z.namelist())
#         zipfiles.sort()
#         if zipfiles:
#             index = len(zipfiles) - 1
#             find_str = ''
#             while index >= 0:
#                 packet_str = z.read(zipfiles[index])
#                 if packet_str.find('/mp/getappmsgext?'):
#                     find_str = packet_str
#                     break
#                 index -= 1
#             h = dpkt.http.Request(find_str + "\n  ")
#             http_header = h.headers
#             url = "http://" + http_header['host'] + h.uri
#             query = urlparse.urlparse(url).query
#             params = urlparse.parse_qs(query)
#             uin = params['uin'][0]
#             key = params['key'][0]


print '\n======================================='
print 'start winpcap'
print '=======================================\n'
sniffer = WxSniffer()
sniffer.start()
while True:
    time.sleep(2)
    print sniffer.get_wxarticle_state('http://mp.weixin.qq.com/s?__biz=MjM5Njc0Njc4MQ==&mid=207205228&idx=1&sn=9e78fb81b2ce947d82881cb4ba0dbb79&key=af154fdc40fed0032904e0d3e853027e7ec082dbd2577e90041cb0a306a381e57b811886e1838fc22d04eabe30ffac97&ascene=1&uin=MzQ4ODY2OTU1&devicetype=Windows+8&version=61010029&pass_ticket=Lnb9s1kCfWm8Cw1kVb2eCkiHu1US%2B7XebBq35z3cuK0Xs2X5HSNLAFxkbnTRi2RQ')

# while True:
#     sniffer.simulate_open_wxarticle(5554)
#     time.sleep(5)
#     print sniffer.get_wxarticle_state('MzAwNTA2NjE2OA==', '205059655', '9fb1b7d533d39b65dde7c1d9eb9ab9c7', '1')
#     time.sleep(30)
