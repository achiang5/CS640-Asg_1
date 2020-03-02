'''
Ethernet learning switch in Python.
Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
from switchyard.lib.userlib import *
from collections import deque

def packetExists(packet_src, lru_list):
    for lru_object in lru_list:
        if list(lru_object.keys())[0] == packet_src:
            return lru_object
    return None

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    mynames = [intf.name for intf in my_interfaces]
    lru_list = deque([])

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
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
        except NoPackets:
            continue
        except Shutdown:
            return

        log_debug ("In {} received packet {} on {}".format(net.name, packet, input_port))
        
        if packet[0].dst in mymacs:
            log_debug("Dropped!")
        elif curr_dest_object in list(lru_list):
            index = list(lru_list).index(curr_dest_object)
            log_debug ("Packet {} sent straight to {}".format(packet, lru_list[index][list(curr_dest_object.keys())[0]]))
            net.send_packet(lru_list[index][list(curr_dest_object.keys())[0]], packet)
        else:
            for intf in my_interfaces:
                if input_port != intf.name:
                    log_debug ("Flooding packet {} to {}".format(packet, intf.name))
                    net.send_packet(intf.name, packet)
    net.shutdown()