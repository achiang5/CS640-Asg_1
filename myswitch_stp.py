'''
Ethernet learning switch in Python.
Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
from switchyard.lib.userlib import *
from collections import deque
from SpanningTreeMessage import SpanningTreeMessage
import time

def packetExists(packet_src, lru_list):
    for lru_object in lru_list:
        if list(lru_object.keys())[0] == packet_src:
            return lru_object
    return None

def getSwitchID(mymacs):
    newmacs = sorted(mymacs)
    return newmacs[0]

# def floodSTP(net, my_interfaces, stp_packet):
#     for intf in my_interfaces:
#             log_debug ("Flooding packet {} to {}".format(stp_packet, intf.name))
#             net.send_packet(intf.name, stp_packet)

def floodSTP(net, my_interfaces, stp_packet, input_port=None):
    for intf in my_interfaces:
        if intf.name == input_port:
            continue
        log_debug ("Flooding packet {} to {}".format(stp_packet, intf.name))
        net.send_packet(intf.name, stp_packet)

def mk_stp_pkt(root_id, hops, switch_id, hwsrc="20:00:00:00:00:01", hwdst="ff:ff:ff:ff:ff:ff"):
    # print(root_id, switch_id)
    spm = SpanningTreeMessage(root_id=str(root_id), hops_to_root=hops, switch_id=str(switch_id))
    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
    pkt = Ethernet(src=hwsrc,
                   dst=hwdst,
                   ethertype=EtherType.SLOW) + spm
    xbytes = pkt.to_bytes()
    p = Packet(raw=xbytes)
    # print(p)
    return p

def regularPacketWork(packet, lru_list, input_port):
    curr_src_object = packetExists(packet[0].src, lru_list)
    if curr_src_object is not None:
        if curr_src_object[1] != input_port:
            curr_src_object[1] = input_port
        else:
            lru_list.remove(curr_src_object)
            lru_list.append(curr_src_object)
    else:
        if len(lru_list) == 5:
            lru_list.popleft()
            lru_list.append({packet[0].src : input_port})
        else:
            lru_list.append({packet[0].src : input_port})
    
    curr_dest_object = packetExists(packet[0].dst, lru_list)
    if curr_dest_object is not None:
        lru_list.remove(curr_dest_object)
        lru_list.append(curr_dest_object)
    return curr_dest_object

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    mynames = [intf.name for intf in my_interfaces]
    lru_list = deque([])

    switch_id = getSwitchID(mymacs)
    root_id = switch_id
    root_switch_id = switch_id
    hops_to_root = 0
    last_stp_time = 0
    root_interface = None
    curr_dest_object = None
    blockedPorts = []

    while True:
        try:
            if root_id == switch_id:
                stp_packet = mk_stp_pkt(root_id, 0, switch_id)
                time.sleep(2)
                floodSTP(net, my_interfaces, stp_packet)
                last_stp_time = time.time()

            if time.time() - last_stp_time > 10:
                root_id = switch_id
                hops_to_root = 0
                blockedPorts.clear()
            
            timestamp,input_port,packet = net.recv_packet()
            incoming_interface = input_port
            if packet[0].ethertype == EtherType.SLOW:
                # do new stuff #piazza pseudocode
                if incoming_interface == root_interface:
                    root_switch_id = packet[1].switch_id
                    hops_to_root = packet[1].hops_to_root + 1
                    root_id = packet[1].switch_id
                    last_stp_time = time.time()
                    stp_packet = mk_stp_pkt(root_id, hops_to_root, switch_id)
                    floodSTP(net, my_interfaces, stp_packet, input_port)
                    continue
                elif packet[1].switch_id < root_id:
                    root_id = packet[1].switch_id
                    root_interface = incoming_interface
                    hops_to_root = packet[1].hops_to_root + 1
                    last_stp_time = time.time()
                    # reset all ports to unblocked state
                    blockedPorts.clear()
                    stp_packet = mk_stp_pkt(root_id, hops_to_root, switch_id)
                    floodSTP(net, my_interfaces, stp_packet, input_port)
                    continue
                elif packet[1].switch_id > root_id:
                    print(packet[1])
                    print(blockedPorts)
                    if incoming_interface in blockedPorts:
                        blockedPorts.remove(packet[1].root)
                    continue
                else:
                    if packet[1].hops_to_root + 1 > hops_to_root:
                        #packet dropped
                        log_debug("Packet Dropped!")
                        continue
                    elif(packet[1].hops_to_root + 1 < hops_to_root or (packet[1].hops_to_root+1==hops_to_root and root_switch_id>packet[1].switch_id)):
                        if incoming_interface in blockedPorts:
                            blockedPorts.remove(incoming_interface)
                        blockedPorts.append(root_interface)
                        hops_to_root = packet[1].hops_to_root + 1
                        root_switch_id = packet[1].switch_id
                        root_interface = incoming_interface
                        last_stp_time = time.time()
                        stp_packet = mk_stp_pkt(root_id, hops_to_root, switch_id)
                        floodSTP(net, my_interfaces, stp_packet, input_port)
                        continue
                    else:
                        blockedPorts.append(incoming_interface)
            else: # regular packets
                curr_dest_object = regularPacketWork(packet, lru_list, input_port)
                log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))
        
                if packet[0].dst in mymacs:
                    log_debug("Dropped!")
                elif curr_dest_object in list(lru_list):
                    index = list(lru_list).index(curr_dest_object)
                    log_debug ("Packet {} sent straight to {}".format(packet, lru_list[index][list(curr_dest_object.keys())[0]]))
                    net.send_packet(lru_list[index][list(curr_dest_object.keys())[0]], packet)
                else:
                    for intf in my_interfaces:
                        if input_port != intf.name and intf.name not in blockedPorts:
                            log_debug ("Flooding packet {} to {}".format(packet, intf.name))
                            net.send_packet(intf.name, packet)
        except NoPackets:
            continue
        except Shutdown:
            return

    net.shutdown()