import xml.etree.ElementTree as etree
import ephem
from .utils import *


class TimeAltAz(object):
    def __init__(self):
        self.tm = None
        self.alt = None
        self.az = None

    def format(self):
        result = formatLocalTime(self.tm) + '  [ ' + self.alt + ' / ' + self.az + ' ]'
        return result

class SatellitePassInfo(object):

    UNICODE_RISE = u'\u21E7'
    UNICODE_SET = u'\u21E9'

    def __init__(self):
        self.mag = ''
        self.start = None
        self.max = None
        self.end = None

    def getDate(self):
        if self.start is not None:
            return self.start.tm
        if self.max is not None:
            return self.max.tm
        if self.end is not None:
            return self.end.tm
        return None

    def format(self):
        result = magMeter(self.mag, -3.0, 1.0, 0.5) + '  '  + formatSign(self.mag) + 'm  '
        if self.start is not None:
            result += SatellitePassInfo.UNICODE_RISE + self.start.format() + '  '
        if self.max is not None:
            result += u'\u2600' + self.max.format() + '  '
        if self.end is not None:
            result += SatellitePassInfo.UNICODE_SET + self.end.format() + '\n'
        return result


class SatellitePasses(object):

    UNICODE_RISE = u'\u21E7'
    UNICODE_SET = u'\u21E9'

    def __init__(self):
        self._observer = None
        self._from = ''
        self._to = ''
        self._passInfos = ()

    def format(self):
        #result = '\nFrom: ' + formatLocalDateTime(self._from) + ' To: ' + formatLocalDateTime(self._to) + '\n'
        result = ''
        for satpass in self._passInfos:
            date = formatLocalDateDDMM(satpass.getDate())
            result += date + ' ' + satpass.format()

        if len(result) == 0:
            result = 'No visible satellite pass.'
        else:
            result = '\n' + result

        return result

    def parseFromXml(self, xml_passes):

        rootn = etree.fromstring(xml_passes)

        if rootn is None:
            return 'Empty response.'

        self._observer = ephem.Observer()

        for xml_node in rootn:
            if xml_node.tag == 'location':
                self._observer.lat, self._observer.long = xmlNodeValue(xml_node, 'lat'), xmlNodeValue(xml_node, 'lng')
            elif xml_node.tag == 'altitude':
                self._observer.elevation = int(float(xml_node.text))
            elif xml_node.tag == 'from':
                self._from = parseIsoDateTime(xml_node.text)
            elif xml_node.tag == 'to':
                self._to = parseIsoDateTime(xml_node.text)
            elif xml_node.tag == 'pass':
                self._passInfos += (self._parseOnePass(xml_node),)

    def _parseOnePass(self, passn):
        pass_info = SatellitePassInfo()
        for xml_node in passn:
            if xml_node.tag == 'magnitude':
                pass_info.mag = xml_node.text
            elif xml_node.tag == 'start':
                pass_info.start = self._parseCoordTime(xml_node)
            elif xml_node.tag == 'max':
                pass_info.max = self._parseCoordTime(xml_node)
            elif xml_node.tag == 'end':
                pass_info.end = self._parseCoordTime(xml_node)
        return pass_info

    def _parseCoordTime(self, coordn):
        coordTime = TimeAltAz()
        for xml_node in coordn:
            if xml_node.tag == 'time':
                coordTime.tm = parseIsoDateTime(xml_node.text)
            elif xml_node.tag == 'alt':
                coordTime.alt = xml_node.text
            elif xml_node.tag == 'az':
                coordTime.az = xml_node.text
        return coordTime
