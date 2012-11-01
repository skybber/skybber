import re
import ephem
import datetime
import math

def xmlNodeValue(parent_node, node_name):
    node = parent_node.find(node_name)
    return '' if node is None else node.text

def parseIsoDateTime(sdate):
    dt = datetime.datetime(*map(int, re.split('[^\d]', sdate)[:-1]))
    return ephem.Date(dt)

def parseXmppDateTime(sdate):
    return parseIsoDateTime(sdate[0:4] + '-' + sdate[4:6] + '-' + sdate[6:])

def formatLocalDateTime(dt):
    return '' if dt is None else ephem.localtime(dt).strftime('%Y-%m-%d %H:%M:%S')

def formatLocalTime(ephmdt):
    return ephem.localtime(ephmdt).strftime('%H:%M:%S')

def formatLocalDate(ephmdt):
    return ephem.localtime(ephmdt).strftime('%Y-%m-%d')

def formatSign(s):
    return float(s) < 0 and str(s) or (' ' + str(s)) 

def magMeter(sm, max_mag, min_mag, step):
    mag = float(sm)
    mag = (mag > min_mag and min_mag) or (mag < max_mag and max_mag) or mag
    koef = 1.0 / step
    meter = "~" * int(round((-max_mag + mag) * koef)) + "#" * int(round((-mag + min_mag) * koef))
    return meter 

def parseArgs(args):
    result = {}
    args = args is None and '' or args.strip()
    if len(args) > 0:
        for a in args.split(' '):
            if '=' in a:
                key, val = a.split('=', 1)
                key = key is None and '' or key.strip()  
                val = val is None and '' or val.strip()  
                if len(key) > 0:
                    result[key] = val
            else:
                result[a] = ''
    return result 

def todegrees(angle_rad):
    return angle_rad / math.pi * 180.0

def toradians(angle_deg):
    return math.pi * angle_deg / 180.0

def is_number(x):
    try:
        float(x)
        return True
    except ValueError:
        return False
    except TypeError:
        return False
