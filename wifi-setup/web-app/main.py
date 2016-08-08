#!/usr/bin/env python
#!/usr/bin/python

import Queue
import threading
import time
import os
import signal

import tornado.ioloop
import tornado.web, tornado.websocket
import tornado.template
import sys
from operator import itemgetter


from server import MainHandler, JSHandler, BootstrapMinJSHandler, BootstrapMinCSSHandler, WSHandler
from WiFiTools import ap_link_tools,dev_link_tools, hostapd_tools
from Config import AppConfig
from FileUtils import ap_mode_config, ap_mode_deconfig
from LinkUtils import ScanForAP, link_add_vap, client_connect_test
config = AppConfig()
config.open_file()
Port = config.ConfigSectionMap("server_port")['port']
WSPort = config.ConfigSectionMap("server_port")['ws_port']
dev_link_tools = dev_link_tools()
linktools = ap_link_tools()

root = os.path.join(os.path.dirname(__file__), "srv/templates")

handlers = [
    (r"/", MainHandler),
    (r"/jquery-2.2.3.min.js",JSHandler),
    (r"/img/(.*)", tornado.web.StaticFileHandler, { 'path': os.path.join(root, 'img/') } ),
    (r"/bootstrap-3.3.7-dist/css/bootstrap.min.css",BootstrapMinCSSHandler),
    (r"/bootstrap-3.3.7-dist/js/bootstrap.min.js",BootstrapMinJSHandler),
    (r"/ws",WSHandler)
]
settings = dict(
    template_path=os.path.join(os.path.dirname(__file__), "srv/templates"),
)

exitFlag = 0

class tornadoWorker (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
    def run(self):
        print "Starting " + self.name + str(self.threadID)
        #process_data(self.name, self.q)
        ws_app = tornado.web.Application([(r'/ws', WSHandler), ])
        ws_app.listen('8888')#Port)
        app = tornado.web.Application(handlers, **settings)
        app.listen('80')
        tornado.ioloop.IOLoop.current().start()
        #print "Exiting " + self.name

class apWorker (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
    def run(self):
        print "Starting " + self.name + str(self.threadID)
        apScan = ScanForAP('scan', 'uap0')
        apScan.start()
        apScan.join()
        ap = apScan.join()

        #################################################
        # Clean up the list of networks.
        #################################################
        # First, sort by name and strength
        nets_byNameAndStr = sorted(ap['network'], key=itemgetter('ssid', 'quality'), reverse=True)
        # now strip out duplicates (e.g. repeaters with the same SSID), keeping the first (strongest)
        lastSSID = "."
        for n in nets_byNameAndStr[:]:
            if (n['ssid'] == lastSSID):
                nets_byNameAndStr.remove(n)
            else:
                lastSSID = n['ssid']
                # Finally, sort by strength alone
            ap['network'] = sorted(nets_byNameAndStr, key=itemgetter('quality'), reverse=True)
        # ap = linktools.scan_ap()
        S = Station()
        try:
            S.station_mode_on()
        except:
            exit(0)
        #process_data(self.name, self.q)
        #print "Exiting " + self.name

class dnsmasqWorker (threading.Thread):
    def __init__(self, threadID, name, q):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.q = q
    def run(self):
        print "Starting " + self.name + str(self.threadID)

        try:
            S.dnsmasq_on()
        except:
            exit(0)
class Station():
    def __init__(self):
        self.aptools = hostapd_tools()
    def station_mode_on(self):
        print "station mode on"
        ap_mode_config()
        self.aptools.hostapd_start()
        #self.aptools.dnsmasq_start()

        #aptools.ap_config()
# SSP: Temporary change while developing
#        AP.copy_config_ap()
#        devtools.link_down()
#        aptools.ap_up()

    def station_mode_off(self):
        print "station mode off"
        #self.aptools.dnsmasq_stop()
        self.aptools.hostapd_stop()

    def dnsmasq_on(self):
        self.aptools.dnsmasq_start()

    def dnsmasq_off(self):
        self.aptools.dnsmasq_stop()
# SSP: Temporary change while developing
#        aptools.ap_down()
#        aptools.ap_deconfig()
#        devtools.link_down()
#        devtools.link_up()

def exit_gracefully(signal, frame):
    print "caught SIGINT"
    S = Station()
    ap_mode_deconfig()
    S.station_mode_off()
    S.dnsmasq_off()
    print "exiting"
    sys.exit(0)



nameList = ['web','ap', 'dns']
queueLock = threading.Lock()
workQueue = Queue.Queue(10)
threads = []
threadID = 1

if __name__ == "__main__":
    signal.signal(signal.SIGINT, exit_gracefully)
    client_connect_test('wlan0', 'MOTOROLA-F29E5', '2e636e8543dc97ee7299')

    link_add_vap()
    ap = ScanForAP("AP SCAN: ", 'uap0')
    ap.start()
    print ap.join()
    #client_connect_test('wlan0', 'MOTOROLA-F29E5', '2e636e8543dc97ee7299')
    # Create new threads
    #for tName in threadList:
    thread = tornadoWorker(threadID, 'web', workQueue)
    thread.setDaemon(True)
    thread.start()
    threads.append(thread)
    threadID += 1
    thread = apWorker(threadID, 'ap', workQueue)
    thread.setDaemon(True)
    thread.start()
    threads.append(thread)
    threadID += 1
    thread = dnsmasqWorker(threadID, 'dns', workQueue)
    thread.start()
    threads.append(thread)
    threadID += 1
    print threading.enumerate()
    # Fill the queue
    queueLock.acquire()
    #for word in nameList:
    #    workQueue.put(word)
    queueLock.release()

    # Wait for queue to empty
    while not workQueue.empty():

        pass

    # Notify threads it's time to exit
    exitFlag = 1

    # Wait for all threads to complete
    #for t in threads:
        #t.is_alive()
#        t.join()
    #print "Exiting Main Thread"