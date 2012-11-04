import xml.etree.ElementTree as etree
import ephem
import utils


class IridiumFlare(object):
    def __init__(self):
        self.mag = None
        self.tm = None
        self.alt = None
        self.az = None
        
    def format(self):
        result = utils.magMeter(self.mag, -8.0, 0.0, 1.0) + '   ' + utils.formatLocalTime(self.tm) + '  ' + \
            utils.formatSign(self.mag) + 'm  [ ' + utils.formatSign(self.alt) + ' / ' + utils.formatSign(self.az) + ' ]\n'
        return result
   
class IridiumFlares(object):

    def __init__(self):
        self._observer = None
        self._from = ''
        self._to = ''
        self._flares = ()
        
    def format(self, min_mag = -2.0):
        # result = '\nFrom: ' + utils.formatLocalDateTime(self._from) + ' To: ' + utils.formatLocalDateTime(self._to) + '\n'
        result = ''
        last_date = '' 
        for flare in self._flares:
            if float(flare.mag) <= min_mag: 
                date = utils.formatLocalDate(flare.tm)
                if date != last_date:
                    result += date + '\n'
                    last_date = date
                result += flare.format()
        if len(result) == 0:
            result = 'No visible flare.'
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
                self._observer.lat, self._observer.long = utils.xmlNodeValue(xml_node, 'lat'), utils.xmlNodeValue(xml_node, 'lng')
            elif xml_node.tag == 'altitude':
                self._observer.elevation = int(float(xml_node.text))
            elif xml_node.tag == 'from':
                self._from = utils.parseIsoDateTime(xml_node.text)
            elif xml_node.tag == 'to':
                self._to = utils.parseIsoDateTime(xml_node.text)
            elif xml_node.tag == 'flare':
                self._flares += (self._parseOneFlare(xml_node),)
                
    def _parseOneFlare(self, passn):
        flare = IridiumFlare()
        for xml_node in passn:
            if xml_node.tag == 'magnitude':
                flare.mag = xml_node.text
            elif xml_node.tag == 'time':
                flare.tm = utils.parseIsoDateTime(xml_node.text) 
            elif xml_node.tag == 'alt':
                flare.alt = xml_node.text
            elif xml_node.tag == 'az':
                flare.az = xml_node.text
        return flare
        
