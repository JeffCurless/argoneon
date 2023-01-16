#!/usr/bin/python3

import sys
import os
import time
import math
sys.path.append( "/etc/argon/" )
from argonsysinfo import *

import argparse

#
def printTable(myDict, colList=None, title : str = None ):
    """ Pretty print a list of dictionarys (myDict) as a dynamically sized table.
    If column names (colList) aren't specified, they will show in random order.
    Author: Therry Husson - Use it as you want but don't blame me.
    """
    if isinstance(myDict, dict):
        myDict = [myDict]

    if title:
        print( f"\n{title}")

    if not colList: colList = list(myDict[0].keys() if myDict else [])
    myList = [colList] # 1st row = header
    for item in myDict: myList.append([str(item[col] if item[col] is not None else '') for col in colList])
    colSize = [max(map(len,col)) for col in zip(*myList)]
    colSep = ' | '
    fullWidth = sum(colSize)+((len(colSize)-1)*len(colSep))
    formatStr = colSep.join(["{{:<{}}}".format(i) for i in colSize])
    myList.insert(1,['-' * i for i in colSize]) # Separating line
    print('-'*fullWidth)
    for item in myList: print( formatStr.format(*item))

    def centre( string ):
        strLen = len(string)
        if strLen < fullWidth:
            padLen = int((fullWidth-strLen)/2)
            if padLen > 0:
                string = string.rjust(strLen+padLen)
        print( string )

    if len(myDict) == 0:
        centre("* No data to display *")
    print( '-'*fullWidth)

#
def show_storage():
    """ Display the storage devices in the system.  These not, devices involved
    in a RAID array are NOT displayed, however the RAID device is.
    """
    devices = argonsysinfo_listhddusage()
    lst = []
    for dev in devices:
        lst.append( {"Device": dev
                    ,"Total": argonsysinfo_kbstr(devices[dev]['total'])
                    ,"Used": argonsysinfo_kbstr(devices[dev]['used'])
                    ,"Pct": f"{devices[dev]['percent']}%"
                    }
                  )
    printTable( lst, ["Device","Total","Used","Pct"], title="Storage Usage:")

#
def show_raid():
    """
    If software RAID is setup, report on the status of the RAID sets.  If there is
    no RAID setup, inform the user.
    """
    raidList = argonsysinfo_listraid()['raidlist']
    lst = []
    rebuildExists = False
    keys = ['Device', 'Type', 'Size', 'State' ]
    for item in raidList:
        stateArray = item['info']['state'].split(", ")
        if len(stateArray) == 1:
            state = stateArray[0]
        elif len(stateArray) == 2:
            state = stateArray[1]
        elif len(stateArray) >= 3:
            state = stateArray[2]
        else:
            state = None
        raidDict = {'Device' : item['title']
                   ,'Type'   : item['info']['raidtype'].upper()
                   ,'Size'   : argonsysinfo_kbstr(item['info']['size'])
                   ,'State'  : state.capitalize()
                   ,'Rebuild': None
                   }
        if len(item['info']['resync']) > 0:
            rebuildExists = True
            raidDict['Rebuild'] = item['info']['resync']
        lst.append( raidDict )

    if rebuildExists:
        keys.append("Rebuild")

    if len(lst) > 0:
        printTable(lst,keys,title="RAID Arrays:" )
    else:
        print( "No RAID Arrays configured!" )

#
def show_cpuUtilization():
    """
    Display the current CPU utilization. Not all that helpful as it is simply a 
    snapshot, and tools such as htop etc work much better.
    """
    lst = [{'CPU': d['title'], "%": d["value"]} for d in argonsysinfo_listcpuusage()]
    printTable( lst, ['CPU','%'], title = 'CPU Utilization')

#
def show_cpuTemperature():
    """
    Display the current CPU temperature
    """
    rawTemp = argonsysinfo_getcputemp()
    ctemp   = argonsysinfo_truncateFloat(rawTemp,2)
    ftemp   = argonsysinfo_convertCtoF(rawTemp,2)
    printTable({"C":ctemp,"F":ftemp},title="CPU Temperature:")

#
def show_ipaddresses():
    """
    Display a list of all Network interfaces configured with IP addresses, with the
    exception of any bridge types setup for containers
    """
    lst = [{"Interface":item[0],'IP':item[1]} for item in argonsysinfo_getipList()]
    printTable(lst,title="IP Addresses:")

#
def show_hddTemperature():
    """
    Display the current temperatures of any disk devices in the system, note that
    this includes the temperature for any NVME device, so you may need to modify your
    fan triggers
    """
    hddTemp = argonsysinfo_gethddtemp()
    lst = []
    for item in hddTemp:
        rawTemp = hddTemp[item]
        ctemp   = argonsysinfo_truncateFloat(rawTemp,1)
        ftemp   = argonsysinfo_convertCtoF(rawTemp,1)
        lst.append( {'Device':item, "C":ctemp, "F":ftemp})
    printTable( lst, title="Storage Temperature:")

#
def show_fanspeed():
    """
    Display the current fan speed percentage.
    """
    printTable({"Speed %" : argonsysinfo_getCurrentFanSpeed()},['Speed %'],title='Fan Speed')

def show_hddutilization():
    """
    Display the current disk device utilization, this is basically useless, use dstat.
    """
    start  = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    usage1 = argonsysinfo_diskusage()
    time.sleep(1)
    usage2 = argonsysinfo_diskusage()
    stop   = time.clock_gettime_ns(time.CLOCK_MONOTONIC)

    for istop in usage2:
        for istart in usage1:
            if istop['disk'] == istart['disk']:
                istart['readsector']  = istop['readsector'] - istart['readsector']
                istart['writesector'] = istop['writesector'] - istart['writesector']
    span = ((stop - start)/1000000000)
    lst = []
    for item in usage1:
        readbw = (item['readsector']/2)/span
        writebw = (item['writesector']/2)/span
        lst.append({'Device':item['disk'], "Read/Sec":argonsysinfo_kbstr(int(readbw)),"Write/Sec":argonsysinfo_kbstr(int(writebw))})
    printTable(lst, title = 'Storage Utilization:' )
#
def show_all():
    show_storage()
    show_raid()
    show_hddTemperature()
    show_cpuUtilization()
    show_cpuTemperature()
    show_ipaddresses()
    show_fanspeed()
    show_memory()

def show_memory():
    memory = argonsysinfo_getram()
    printTable({"Total":memory[1],"Free":memory[0]},title="Memory:")

#
def print_version():
    print( 'Currently running version 2023.01.15-01')

#
def setup_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument( '-v', '--version', action='store_true', help='Display the version of the argon scripts.')
    parser.add_argument( '-a', '--all',     action='store_true', help='Display full status of the Argon EON.')
    parser.add_argument( '-c', '--cpu',     action='store_true', help='Display the current CPU utilization.')
    parser.add_argument( '-d', '--devices', action='store_true', help='Display informaton about devices in the EON.')
    parser.add_argument( '-f', '--fan',     action='store_true', help='Get current fan speed.')
    parser.add_argument( '-i', '--ip',      action='store_true', help='Display currently configured IP addresses.')
    parser.add_argument( '-m', '--memory',  action='store_true', help='Display memory utilization on the EON.')
    parser.add_argument( '-r', '--raid',    action='store_true', help='Display current state of the raid Array if it exists.')
    parser.add_argument( '-s', '--storage', action='store_true', help='Display information about the storage system.')
    parser.add_argument( '-t', '--temp',    action='store_true', help='Display information about the current temperature.')
    parser.add_argument( '-u', '--hdduse',  action='store_true', help='Display disk utilization.')
    parser.add_argument( '--hddtemp',       action='store_true', help='Display the temperature of the storage devices.')
    return parser

#

start = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
usage1= argonsysinfo_diskusage()

def main():
    parser = setup_arguments()
    if len(sys.argv) > 1:
        args = parser.parse_args()
    elif 'ARGON_STATUS_DEFAULT' in os.environ:
        commands = os.environ['ARGON_STATUS_DEFAULT'].split(" ")
        args = parser.parse_args(commands)
    else:
        args = parser.parse_args(['--devices','--ip'])

    if args.version :
        print_version()
    if args.cpu:
        show_cpuUtilization()
    if args.devices:
        show_hddTemperature()
        show_storage()
        show_raid()
    if args.fan:
        show_fanspeed()
    if args.raid :
        show_raid()
    if args.storage :
        show_storage()
    if args.temp :
        show_cpuTemperature()
    if args.hddtemp:
        show_hddTemperature()
    if args.ip:
        show_ipaddresses()
    if args.memory:
        show_memory()
    if args.hdduse:
        show_hddutilization()
    if args.all:
        show_all()
    
if __name__ == "__main__":
    setup_arguments()
    main()
