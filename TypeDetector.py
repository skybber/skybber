# coding: utf-8

import math
import re

class TypeDetector(object):

    NONE = 0
    INTEGER = 1
    FLOAT = 2
    LOCATION_LONG = 3
    LOCATION_LAT = 4
    STRING = 5
    
    re_location = re.compile(unicode('(\d{1,3})°(\d{1,2})\'(?:(\d{1,2})(?:\.(\d+))?\")?([NSEW])'))
    
    ''' TypeDetector class
    '''
    def __init__(self, s):
        self._type = TypeDetector.NONE
        self._typeValue = None
        self._value = s
        self._checkType(s)


    def _checkType(self, s):
        ''' Detect type inside string and converts value to detected type 
        '''
        try:
            self._typeValue = int(s)
            self._type = TypeDetector.INTEGER
            return
        except:
            pass

        try:
            self._typeValue = float(s)
            self._type = TypeDetector.FLOAT
            return
        except:
            pass
        
        if self._checkLocation(s):
            return
        
        self._typeValue = s
        self._type = TypeDetector.STRING 
        
    def _checkLocation(self, v):
        ''' Checks if string has location format
        '''
        m = re.match(TypeDetector.re_location, v)
        
        if m is None:
            return False
        
        deg_angle = float(m.group(1)) + float(m.group(2)) / 60.0
        
        if m.group(3) is not None:
            if m.group(4) is not None: 
                deg_angle += float(m.group(3) + '.' + m.group(4)) / 3600.0
            else:
                deg_angle += float(m.group(3)) / 3600.0
                
        if m.group(5) == 'W':
            self._type = TypeDetector.LOCATION_LONG
            self._typeValue = -deg_angle
        elif m.group(5) == 'E':
            self._type = TypeDetector.LOCATION_LONG
            self._typeValue = deg_angle
        elif m.group(5) == 'N':
            self._type = TypeDetector.LOCATION_LAT
            self._typeValue = deg_angle
        else:
            self._type = TypeDetector.LOCATION_LAT
            self._typeValue = -deg_angle

        return True

    def isNumber(self):
        return self._type in { TypeDetector.INTEGER, TypeDetector.FLOAT } 
    
    def getValue(self):
        return self._value

    def getType(self):
        return self._type
    
    def getTypeValue(self):
        return self._typeValue

    def getRadAngle(self):
        if self._type in { TypeDetector.LOCATION_LONG, TypeDetector.LOCATION_LAT }:
            return math.pi * self.getTypeValue(self) / 180.0
        return None   
