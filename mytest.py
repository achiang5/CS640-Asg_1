#!/usr/bin/env python3
from switchyard.lib.userlib import *

def mk_pkt(hwsrc, hwdst, ipsrc, ipdst, reply=False):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=32)
    icmppkt = ICMP()
    if reply:
        icmppkt.icmptype = ICMPType.EchoReply
    else:
        icmppkt.icmptype = ICMPType.EchoRequest
    return ether + ippkt + icmppkt

def hub_tests():
    s = TestScenario("Switch Tests")
    s.add_interface('eth0', '20:00:00:00:00:01')
    s.add_interface('eth1', '20:00:00:00:00:02')
    s.add_interface('eth2', '20:00:00:00:00:03')

    reqpkt = mk_pkt("60:00:00:00:00:01", "70:00:00:00:00:01", '192.168.1.100', '172.16.42.2')
    s.expect(PacketInputEvent("eth0", reqpkt, display=Ethernet),
             "An Ethernet frame from 60:00:00:00:00:00 to 70:00:00:00:00:01 should arrive on eth0")
    s.expect(PacketOutputEvent("eth2", reqpkt, display=Ethernet),
             "Ethernet frame destined for 70:00:00:00:00:01 should be flooded out eth2")





scenario = hub_tests()
