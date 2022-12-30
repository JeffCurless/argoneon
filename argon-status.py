#!/usr/bin/python3

import sys
import os
import time
import math
sys.path.append( "/etc/argon/")
from argonsysinfo import *

from argononed import getCurrentFanSpeed

usage1 = argonsysinfo_diskusage()
start = time.clock_gettime_ns(time.CLOCK_MONOTONIC)


def printTable(myDict, colList=None, title : str = None):
   """ Pretty print a list of dictionaries (myDict) as a dynamically sized table.
   If column names (colList) aren't specified, they will show in random order.
   Author: Thierry Husson - Use it as you want but don't blame me.
   """
   if isinstance(myDict,dict):
        myDict = [myDict]
        
   if title:
      print (f"\n{title}")

   if not colList: colList = list(myDict[0].keys() if myDict else [])
   myList = [colList] # 1st row = header
   for item in myDict: myList.append([str(item[col] if item[col] is not None else '') for col in colList])
   colSize = [max(map(len,col)) for col in zip(*myList)]
   colSep = ' | '
   fullWidth = sum(colSize)+((len(colSize)-1)*len(colSep))
   formatStr = colSep.join(["{{:<{}}}".format(i) for i in colSize])
   myList.insert(1, ['-' * i for i in colSize]) # Seperating line
   
   print ('-'*fullWidth)
   for item in myList: print(formatStr.format(*item))
   
   def centre (string):
     strLen = len(string)
     if strLen < fullWidth:
        padLen = int((fullWidth-strLen)/2)
        if padLen > 0:
            string = string.rjust(strLen+padLen)
     print (string)
   if len (myDict) == 0:
      centre ("* No data to display *")
   print ('-'*fullWidth)

#
# Display CPU Utilization
# 
printTable([{"CPU" : d["title"], "%" : d["value"] } for d in argonsysinfo_listcpuusage()]
          ,['CPU','%']
          ,title = 'CPU Utilisation:'
          )


printTable({"Speed %" : getCurrentFanSpeed()}
          ,['Speed %']
          ,title = 'Fan Speed'
          )

#
# Display Usage
#
hddlist = argonsysinfo_listhddusage()

lst = []
for dev in hddlist:
    lst.append ({"Device": dev
                ,"Total": argonsysinfo_kbstr(hddlist[dev]['total'])
                ,"Used": argonsysinfo_kbstr(hddlist[dev]['used'])
                ,"Pct": f"{hddlist[dev]['percent']}%"
                }
               ) 
printTable(lst,["Device","Total","Used","Pct"], title = "Storage Usage:")

#
# Display RAID
#
raidlist = argonsysinfo_listraid()['raidlist']
lst = []
rebuildExists=False
keys = ['Device','Type','Size','State']
for item in raidlist:
    stateArray = item['info']['state'].split( ", " )
    if len(stateArray) == 1:
        state = stateArray[0]
    elif len(stateArray) == 2:
        state = stateArray[1]
    elif len(stateArray) >= 3:
        state = stateArray[2]
    else:
        state = None
    thisDict = {'Device'  : item['title']
               ,'Type'    : item['info']['raidtype'].upper()
               ,'Size'    : argonsysinfo_kbstr(item['info']['size'])
               ,'State'   : state.capitalize()
               ,'Rebuild' : None
               }
    if len(item['info']['resync']) > 0:
        rebuildExists = True
        thisDict['Rebuild'] = item['info']['resync']
    lst.append (thisDict)

if rebuildExists:
    keys.append ("Rebuild")


if len(lst) > 0 :
    printTable(lst,keys, title = "RAID Arrays:" )
#print( "Drives used in RAID:" )
#print( hddlist )
#
# Display memory usage
#
tmp = argonsysinfo_getram()
printTable({"Total":tmp[1],"Free":tmp[0]},title="Memory:")
#
# Display temp
#
def CtoF (celcius):
    return (32 + (9*celcius)/5)

def smarterRound (value, dp = 1):
    val = round(value,dp)
    if dp > 0:
        val = str(val).rstrip('0').rstrip('.')
    return val

rawtemp = argonsysinfo_getcputemp()
ctemp   = smarterRound(rawtemp)
ftemp   = smarterRound(CtoF(rawtemp),2)

printTable({"°C":ctemp,"°F":ftemp},title = "CPU Temp:")
#

tmp = argonsysinfo_gethddtemp()
lst = []
for item in tmp:
    rawtemp = tmp[item]
    ctemp   = smarterRound(rawtemp)
    ftemp   = smarterRound(CtoF(rawtemp),2)
    lst.append ({'Device': item, "°C":ctemp,"°F":ftemp})
printTable(lst,title = "HDD Temp:")    



#
# Display IP address
#
lst = [{"Interface":item[0], 'IP':item[1]} for item in argonsysinfo_getipList()]
printTable(lst,title = "IP Addresses:")    

#
# Disk Utilization
# 
usage2 = argonsysinfo_diskusage()
stop = time.clock_gettime_ns(time.CLOCK_MONOTONIC)

for istop in usage2:
    for istart in usage1:
        if istop['disk'] == istart['disk']:
            istop['readsector'] = istop['readsector'] - istart['readsector']
            istop['writesector'] = istop['writesector'] - istart['writesector']

span = ((stop - start)/1000000000)
lst = []
for item in usage2:
    readbw = (item['readsector']/2)/span
    writebw = (item['writesector']/2)/span
    lst.append ({'Device': item['disk'], "Read/Sec": argonsysinfo_kbstr(int(readbw)), "Write/Sec" : argonsysinfo_kbstr(int(writebw))})
printTable(lst,title = "Disk Utilisation:")    
    


