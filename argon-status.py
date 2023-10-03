#!/usr/bin/python3

import sys
import os
import subprocess
import time
import math
import json
sys.path.append( "/etc/argon/" )
from argonsysinfo import *
from argonconfig import *
from version import *
import argparse
from collections import ChainMap

#
def prepareJSON(data):

    values = data.get('values', None)
    title = data.get('title', None)
    json_dict={}

    title = title.lower()
    title = title.replace(':','')
    title = title.replace(' ', '_' )

    json_dict[title] = values
    return json_dict

#
def printJSON(data):

    if (args.all != True) and (args.cooling != True):
        data = prepareJSON(data)

    print(json.dumps(data, indent=4), end = '')


#
def printTable(data):
    """ Pretty print a list of dictionarys (myDict) as a dynamically sized table.
    If column names (headers) aren't specified, they will show in random order.
    Author: Therry Husson - Use it as you want but don't blame me.
    """

    if data == None:
        return

    title = data.get('title', None)
    headers = data.get('headers', None)
    values = data.get('values', None)

    if values == None:
        return

    if len(values) == 0:
        return

    if title:
        print( f"\n{title}")

    if headers:
        for head in headers:
            print(f'{head: <14}', end='')
        print()
    else:
        for _key, item in values[0].items():
            print(f'{_key: <14}', end='')
        print()

    for value in values:
        for _key, item in value.items():
            print(f'{str(item): <14}', end='')
        print()

    return


#
def printOutput(data):
    if args.json == True:
        printJSON(data)
    else:
        printTable(data)

#
def show_storage():
    """ Display the storage devices in the system.  These not, devices involved
    in a RAID array are NOT displayed, however the RAID device is.
    """
    temp_result = {}
    result = {}
    devices = argonsysinfo_listhddusage()
    values = []
    for dev in devices:
        values.append( {"Device": dev
                    ,"Total": argonsysinfo_kbstr(devices[dev]['total'])
                    ,"Used": argonsysinfo_kbstr(devices[dev]['used'])
                    ,"Percent": f"{devices[dev]['percent']}"
                    }
                  )


    result['values'] = values
    result['headers'] = ["Device","Total","Used","Percent"]
    result['title'] = 'Storage Usage:'
    return result


#
def show_raid():
    """
    If software RAID is setup, report on the status of the RAID sets.  If there is
    no RAID setup, inform the user.
    """
    raidList = argonsysinfo_listraid()['raidlist']
    values = []
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
        values.append( raidDict )

    if rebuildExists:
        keys.append("Rebuild")

    if len(values) > 0:
        result = {}
        result['title'] = "RAID Arrays:"
        result['values'] = values
        return result
    else:
        print( "No RAID Arrays configured!" )
        return None

#
def show_cpuUtilization():
    """
    Display the current CPU utilization. Not all that helpful as it is simply a 
    snapshot, and tools such as htop etc work much better.
    """
    values = [{'CPU': d['title'], "%": d["value"]} for d in argonsysinfo_listcpuusage()]

    result = {}
    result['title'] = 'CPU Utilization:'
    result['headers'] = ['CPU','%']
    result['values'] = values
    return result


#
def show_cpuTemperature():
    """
    Display the current CPU temperature
    """
    rawTemp = argonsysinfo_getcputemp()
    ctemp   = argonsysinfo_truncateFloat(rawTemp,2)
    ftemp   = argonsysinfo_convertCtoF(rawTemp,2)

    result = {}
    result['title'] = 'CPU Temperature:'
    result['values'] = [{"C":ctemp,"F":ftemp}]
    return result


#
def show_ipaddresses():
    """
    Display a list of all Network interfaces configured with IP addresses, with the
    exception of any bridge types setup for containers
    """
    values = [{"interface": item[0], 'ip':item[1]} for item in argonsysinfo_getipList()]
    result = {}
    result['title'] = 'IP Addresses:'
    result['values'] = values
    return result


#
def show_hddTemperature():
    """
    Display the current temperatures of any disk devices in the system, note that
    this includes the temperature for any NVME device, so you may need to modify your
    fan triggers
    """
    hddTemp = argonsysinfo_gethddtemp()
    values = []
    for item in hddTemp:
        rawTemp = hddTemp[item]
        ctemp   = argonsysinfo_truncateFloat(rawTemp,1)
        ftemp   = argonsysinfo_convertCtoF(rawTemp,1)
        values.append( {'device':item, "C":ctemp, "F":ftemp})

    result = {}
    result['title'] = 'Storage Temperature:'
    result['values'] = values
    return result


#
def show_fanspeed():
    """
    Display the current fan speed percentage.
    """
    result = {}
    result['title'] = 'Fan Speed:'
    result['headers'] = ['percent']
    result['values'] = [{"percent" : argonsysinfo_getCurrentFanSpeed()}]
    return result


#
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
    values = []
    for item in usage1:
        readbw = (item['readsector']/2)/span
        writebw = (item['writesector']/2)/span
        values.append({'Device':item['disk'], "Read/Sec":argonsysinfo_kbstr(int(readbw)),"Write/Sec":argonsysinfo_kbstr(int(writebw))})

    result = {}
    result['title'] = 'Storage Utilization:'
    result['values'] = values
    return result


#
def show_all(show_list):
    """ 
    Display all options that we care about
    """
    all_list = {}
    for show in show_list:
        result = globals()[f'show_{show}']()
        if args.json:
            result = prepareJSON(result)
            all_list = {**all_list, **result}
        else:
            printOutput(result)

    if args.json:
        printOutput(all_list)


#
def show_memory():
    """
    Display currnent memory utilization
    """
    memory = argonsysinfo_getram()

    result = {}
    result['title'] = 'Memory:'
    result['values'] = [{"Total GB":memory['gb'],"Free percent":memory['percent']}]
    return result

#
def print_version():
    """ 
    Display the version of we are currently running
    """
    print( 'Currently running version: ' + ARGON_VERSION )

#
def setup_arguments():
    """
    Setup all of the arguments that we recoginize.  
    """
    parser = argparse.ArgumentParser()
    parser.add_argument( '-v', '--version', action='store_true', help='Display the version of the argon scripts.')
    parser.add_argument( '-a', '--all',     action='store_true', help='Display full status of the Argon EON.')
    parser.add_argument( '-c', '--cpu',     action='store_true', help='Display the current CPU utilization.')
    parser.add_argument( '-d', '--devices', action='store_true', help='Display informaton about devices in the EON.')
    parser.add_argument( '-f', '--fan',     action='store_true', help='Get current fan speed.')
    parser.add_argument( '-i', '--ip',      action='store_true', help='Display currently configured IP addresses.')
    parser.add_argument( '-j', '--json',    action='store_true', help='Display output in json format')
    parser.add_argument( '-m', '--memory',  action='store_true', help='Display memory utilization on the EON.')
    parser.add_argument( '-r', '--raid',    action='store_true', help='Display current state of the raid Array if it exists.')
    parser.add_argument( '-s', '--storage', action='store_true', help='Display information about the storage system.')
    parser.add_argument( '-t', '--temp',    action='store_true', help='Display information about the current temperature.')
    parser.add_argument( '-u', '--hdduse',  action='store_true', help='Display disk utilization.')
    parser.add_argument( '--hddtemp',       action='store_true', help='Display the temperature of the storage devices.')
    parser.add_argument( '--cooling',       action='store_true', help='Display cooling information about the EON.')
    return parser

def show_config():
    """
    Create a table of the HDD and CPU temperatures, and then add in all of the marked fan
    speeds for the given temps.  We also highlight the thing that is forcing the current fanspeed.
    """
    hddtempvalues = loadHDDFanConfig()
    cputempvalues = loadCPUFanConfig()
  
    actualcpu = argonsysinfo_getcputemp()
    actualhdd = argonsysinfo_getmaxhddtemp()
    fanspeed  = argonsysinfo_getCurrentFanSpeed()
    keys = {}
    hdd = {'Temperature':'HDD fanspeed'}
    cpu = {'Temperature':'CPU fanspeed'}
    for i in hddtempvalues.keys():
        keys.__setitem__( i, '' )

    for i in cputempvalues.keys():
        keys.__setitem__( i, '' )

    for i in sorted(keys.keys()):
        if i in hddtempvalues.keys():
            if float(actualhdd) >= float(i) and (int(hddtempvalues[i]) == int(fanspeed)):
                hdd.__setitem__( i, '<' + hddtempvalues[i] + '>' )
            else:
                hdd.__setitem__(i,hddtempvalues[i] )
        else:
            hdd.__setitem__( i, '' )
        if i in cputempvalues.keys():
            if (float(actualcpu) >= float(i)) and (int(cputempvalues[i]) == int(fanspeed)):
                cpu.__setitem__( i, "<" + cputempvalues[i] + ">" )
            else:
                cpu.__setitem__( i, cputempvalues[i] )
        else:
            cpu.__setitem__( i, '' )

    values = []
    values.append( hdd )
    values.append( cpu )

    result = {}
    result['title'] = 'Temperature Settings Table:'
    result['values'] = values
    return result

#
def check_permission():
    """
    Determine if the user can properly execute the script.  Must have sudo or be root
    """
    if not ('SUDO_UID' in os.environ ) and os.geteuid() != 0:
        return False
    return True

#
def main():
    """
    Process all command line options here.  This is where we modify the default settings based on the evironment
    variable AGON_STATUS_DEFAULT.  If there are any flags that cannot be used together, filter them out here.
    """
    global args
    global parser

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
        result = show_cpuUtilization()
        printOutput(result)
    if args.devices:
        show_devices_list = [
            "hddTemperature",
            "storage",
            "raid"]
        show_all( show_devices_list )
    if args.fan:
        result = show_fanspeed()
        printOutput(result)
    if args.raid :
        result = show_raid()
        printOutput(result)
    if args.storage :
        result = show_storage()
        printOutput(result)
    if args.temp :
        result = show_cpuTemperature()
        printOutput(result)
    if args.hddtemp:
        result = show_hddTemperature()
        printOutput(result)
    if args.ip:
        result = show_ipaddresses()
        printOutput(result)
    if args.memory:
        result = show_memory()
        printOutput(result)
    if args.hdduse:
        result = show_hddutilization()
        printOutput(result)
    if args.all:
        show_all_list = [
            "storage",
            "raid",
            "hddTemperature",
            "cpuUtilization",
            "cpuTemperature",
            "ipaddresses",
            "fanspeed",
            "memory"
            ]
        show_all(show_all_list)
    if args.cooling:
        show_cooling_list = [
            "cpuTemperature",
            "hddTemperature",
            "fanspeed",
            "config"
            ]
        show_all(show_cooling_list)


if __name__ == "__main__":
    main()
