# coding: utf-8

import math
import re
import datetime

class TypeDetector(object):
    """ TypeDetector class
    """

    NONE = 0
    INTEGER = 1
    FLOAT = 2
    LOCATION_LONG = 3
    LOCATION_LAT = 4
    DATE = 5
    STRING = 6
    
    re_location = re.compile(u'^(\d{1,3})°(\d{1,2})\'(?:(\d{1,2})(?:\.(\d+))?\")?([NSEW])$')
    re_date = re.compile('^(?:(\d{4})-(\d{1,2})-(\d{1,2}))|(?:(\d{4})/(\d{1,2})/(\d{1,2}))$')
    
    def __init__(self, s):
        self._type = TypeDetector.NONE
        self._typeValue = None
        self._value = s
        self._checkType(s)


    def _checkType(self, s):
        """ Detect type inside string and converts value to detected type 
        """
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

        if self._checkDate(s):
            return

        self._typeValue = s
        self._type = TypeDetector.STRING 
        
    def _checkDate(self, s):
        m = re.match(TypeDetector.re_date, s)

        if m is None:
            return False
        
        if m.group(1) is not None:
            year, month, day = m.group(1), m.group(2), m.group(3)
        else: 
            year, month, day = m.group(4), m.group(5), m.group(6)
        
        try:
            self._typeValue = datetime.date(int(year), int(month), int(day))
            self._type = TypeDetector.DATE
            return True
        except ValueError:
            pass 
        return False

    def _checkLocation(self, s):
        """ Checks if string has location format
        """
        m = re.match(TypeDetector.re_location, s)
        
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
