# SkybberBot: Astronomical jabber/xmpp bot 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from boto.gs.connection import Location
from iriflares import IridiumFlares
from jabberbot import botcmd
from location import Location
from mucjabberbot import MUCJabberBot
from satellitepass import SatellitePasses
from user import User
import datetime
import ephem
import math
import sqlite3
import urllib2
import utils

class MasterDBConnection():
    SKYBBER_DB = 'skybber.db'

    def __init__(self):
        self.dbcon = None
    def __enter__(self):
        self.dbcon = sqlite3.connect(self.SKYBBER_DB)
        return self.dbcon.cursor()
    def __exit__(self, type, value, tb):
        if tb is None:
            self.dbcon.commit()
            self.dbcon.close()
            self.dbcon = None
        else:
            self.dbcon.rollback()
            self.dbcon.close()
            self.dbcon = None
            
class SkybberBot(MUCJabberBot):
    
    AVAILABLE, AWAY, CHAT = None, 'away', 'chat'
    DND, XA, OFFLINE = 'dnd', 'xa', 'unavailable'
    MSG_AUTHORIZE_ME = 'Skybber: Please authorize my request.'
    MSG_NOT_AUTHORIZED = 'You did not authorize my subscription request. Access denied.'
    MSG_UNKNOWN_COMMAND = 'Unknown command: "%(command)s". Type "%(helpcommand)s" for available commands.'
    MSG_HELP_TAIL = 'Type %(helpcommand)s <command name> to get more info about that specific command.'
    MSG_HELP_UNDEFINED_COMMAND = 'Undefined command.'
    MSG_ERROR_OCCURRED = 'Unexpected error.'

    PING_FREQUENCY = 60  # Set to the number of seconds, e.g. 60.
    PING_TIMEOUT = 2  # Seconds to wait for a response.
    
    ''' SkybberBot - Astronomical jabber robot
    '''
    def __init__(self, *args, **kwargs):
        MUCJabberBot.__init__(self, *args, **kwargs)
        self._obsr_default = ephem.Observer()
        self._obsr_default.long, self._obsr_default.lat = '15.05728', '50.76111'
        self._obsr_default.elevation = 400  

    @botcmd
    def satinfo(self, mess, args):
        ''' information about satellite identified by satellite id
        '''
        if args is None or len(args) == 0:
            return '<b>Usage:</b> satinfo satelliteID'

        try:
            satid = int(args)

            opener = urllib2.build_opener()
            opener.addheaders = [
                ('Accept', 'application/xml'), # Change this to applicaiton/xml to get an XML response
            ]
            
            req = urllib2.Request('http://api.uhaapi.com/satellites/' + str(satid) , None, {})

            reply = opener.open(req).read()
            self.send_simple_reply(mess, reply)
            
        except ValueError as e:
            return '<b>Usage:</b> satinfo satelliteID'
            print e
        except urllib2.URLError as e:
            print e
        
    @botcmd
    def satpass(self, mess, args):
        ''' shows satellite passes identified by satellite id
        '''
        if args is None or len(args) == 0:
            return '<b>Usage:</b> satpass satellite ID'

        try:
            satid = int(args)
            return self._satteliteRequest(mess, args, str(satid), self._getObserver(mess.getFrom().getStripped()))
        except ValueError as e:
            return '<b>Usage:</b> satpass satellite ID'
            print e

    @botcmd
    def iss(self, mess, args):
        ''' shows ISS passes
        '''
        return self._satteliteRequest(mess, args, '25544', self._getObserver(mess.getFrom().getStripped()))

    @botcmd
    def iri(self, mess, args):
        ''' shows Iridium flares
        '''
        opener = urllib2.build_opener()
        opener.addheaders = [
            ('Accept', 'application/xml'), # Change this to applicaiton/xml to get an XML response
        ]
        
        lon, lat = self._getObserverStrCoord(mess.getFrom().getStripped())
        req = urllib2.Request('http://api.uhaapi.com/satellites/iridium/flares?lat=' + lat + '&lng=' + lon, None, {})
        try:
            reply = opener.open(req).read()
            iflares = IridiumFlares()
            iflares.parseFromXml(reply)
            fmt_txt = iflares.format() 
            self.send_simple_reply(mess, fmt_txt)
        except urllib2.URLError as e:
            self.send_simple_reply(mess, 'Service disconnected.')
            print e
    

    def _satteliteRequest(self, mess, args, satid, observer):
        opener = urllib2.build_opener()
        opener.addheaders = [
            ('Accept', 'application/xml'), # Change this to applicaiton/xml to get an XML response
        ]

        lon, lat = self._getObserverStrCoord(mess.getFrom().getStripped())

        req = urllib2.Request('http://api.uhaapi.com/satellites/' + satid + '/passes?lat=' + lat + '&lng=' + lon, None, {})
        try:
            reply = opener.open(req).read()
            sp = SatellitePasses()
            sp.parseFromXml(reply)
            fmt_txt = sp.format() 
            self.send_simple_reply(mess, fmt_txt)
        except urllib2.URLError as e:
            self.send_simple_reply(mess, 'Service disconnected.')
            print e
    
    @botcmd
    def tw(self, mess, args):
        ''' shows begin/end of current twilight  
        '''
        body = ephem.Sun()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '-18.0', datetime.datetime.utcnow())
        reply = 'v' + utils.formatLocalTime(next_setting) + '  -  ^' + utils.formatLocalTime(next_rising) 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def sun(self, mess, args):
        ''' shows sun info  
        '''
        body = ephem.Sun()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = 'v' + utils.formatLocalTime(next_setting) + '  -  ^' + utils.formatLocalTime(next_rising) 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def moon(self, mess, args):
        ''' shows Moon ephemeris  
        '''
        body = ephem.Moon()
        body.compute()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = '^' + utils.formatLocalTime(next_rising) + ' -  v' + utils.formatLocalTime(next_setting)
        reply += '  Phase ' +  "{0:.2f}".format(body.phase) 
        reply += '  [ ' +  ephem.constellation(body)[1] + ' ]' 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def mer(self, mess, args):
        ''' shows Mercury ephemeris  
        '''
        body = ephem.Mercury()
        body.compute()
        elong = math.degrees(body.elong)
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        if elong > 0.0:
            reply = 'v' + utils.formatLocalTime(next_setting)
        else:
            reply = '^' + utils.formatLocalTime(next_rising)
        reply += '  ' + str(body.mag) + 'm'
        reply += '  Elong ' + "{0:.2f}".format(elong)
        reply += '  [ ' +  ephem.constellation(body)[1] + ' ]' 
        self.send_simple_reply(mess, reply)
    
    @botcmd 
    def ven(self, mess, args):
        ''' shows Venus ephemeris  
        '''
        body = ephem.Venus()
        body.compute()
        elong = math.degrees(body.elong)
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        if elong > 0.0:
            reply = 'v' + utils.formatLocalTime(next_setting)
        else:
            reply = '^' + utils.formatLocalTime(next_rising)
        reply += '  ' + str(body.mag) + 'm'
        reply += '   Elong ' + "{0:.2f}".format(elong)
        reply += '  [ ' +  ephem.constellation(body)[1] + ' ]' 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def mar(self, mess, args):
        ''' shows Mars ephemeris  
        '''
        body = ephem.Mars()
        body.compute()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = utils.formatRiseSet(body, next_rising, next_setting)
        self.send_simple_reply(mess, reply)

    @botcmd 
    def jup(self, mess, args):
        ''' shows Jupiter ephemeris  
        '''
        body = ephem.Jupiter()
        body.compute()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = utils.formatRiseSet(body, next_rising, next_setting)
        self.send_simple_reply(mess, reply)

    @botcmd 
    def sat(self, mess, args):
        ''' shows Saturn ephemeris  
        '''
        body = ephem.Saturn()
        body.compute()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = utils.formatRiseSet(body, next_rising, next_setting)
        self.send_simple_reply(mess, reply)

    def _getNextRiseSetting(self, jid, body, horizon, dt):
        observer = self._getObserverCopy(jid)
        observer.horizon = horizon
        observer.date = ephem.Date(dt) 
        next_rising = observer.next_rising(body)
        next_setting = observer.next_setting(body)
        return next_rising, next_setting 

    @botcmd 
    def reg(self, mess, args):
        ''' registers user into skybber  
        '''
        with MasterDBConnection() as c:
            str_jid = mess.getFrom().getStripped()
            user, _ = self._getUser(c, str_jid, reg_check=False)
            if user is not None:
                reply = 'User ' + str_jid + ' is already registered !' 
            else:
                c.execute('INSERT INTO users(jid, descr) VALUES ( ?, ? )', (mess.getFrom().getStripped(), 'description'))
                reply = 'User ' + str_jid + ' is registered.' 
        
        self.send_simple_reply(mess, reply)

    @botcmd 
    def unreg(self, mess, args):
        ''' unregister user from skybber  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                c.execute('DELETE FROM users WHERE jid=?', (user.getJID(), ))
                c.execute('DELETE FROM locations WHERE user_id=?', (user.getUserId(), ))
                reply = 'User ' + user.getJID() + ' was unregistered.' 
        
        self.send_simple_reply(mess, reply)
        

    @botcmd 
    def prof(self, mess, args):
        ''' shows user profile  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                reply = '\nJID :' + user.getJID() + '\nDescription: ' + user.getProfileDescription() + '\nDefault location: '
                loc = self._getUserDefaultLocation(c, user)
                if loc is None:
                    reply += 'undefined.'
                else:
                    reply += loc.getName()
        self.send_simple_reply(mess, reply)
            
    @botcmd 
    def addloc(self, mess, args):
        ''' adds user location  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                pargs = utils.parseArgs(args)
                if 'name' in pargs and 'lat' in pargs and 'long' in pargs:
                    c.execute('INSERT INTO locations(user_id, name, long, lat) VALUES (?,?,?,?)', \
                              (user.getUserId(), pargs['name'], float(pargs['long']), float(pargs['lat'])))
                    reply = 'Location added. (' + pargs['name'] + '[' + pargs['long'] + ',' + pargs['lat'] + '])'  
                else:
                    reply = 'Invalid command option. Usage: addloc name=<location name> long=<longitude> lat=<latitude>' 

        self.send_simple_reply(mess, reply)

    @botcmd 
    def rmloc(self, mess, args):
        ''' removes location.  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                pargs = utils.parseArgs(args)
                if 'name' in pargs:
                    c.execute('DELETE FROM locations WHERE user_id=? AND name=?', (user.getUserId(), pargs['name']))
                    reply = 'Location "' + pargs['name'] + '" was removed.'  
                else:
                    reply = 'Invalid command option. Usage: rmloc name=NAME' 

        self.send_simple_reply(mess, reply)

    @botcmd 
    def setloc(self, mess, args):
        ''' set location.  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                rs = c.execute("SELECT location_id FROM locations WHERE name=?", (args, )).fetchone()
                if rs is not None:
                    c.execute("UPDATE users SET default_location_id=? WHERE user_id=?", (rs[0], user.getUserId(),))
                    reply = 'Default location is: ' + args 
                else:
                    reply = 'Unknown location: ' + args 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def lsloc(self, mess, args):
        ''' list of locations  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                rs = c.execute("SELECT name, long, lat FROM locations WHERE user_id=?", (user.getUserId(), ))
                reply = '\nUser locations : \n'
                for loc in rs:
                    reply += loc[0] + ' [' + str(loc[1]) + ', ' + str(loc[2]) + ']\n' 
        self.send_simple_reply(mess, reply)

    def _getUser(self, c, strjid, reg_check=True):
        rs = c.execute("SELECT user_id, jid, descr, default_location_id FROM users WHERE jid=?", (strjid, )).fetchone()
        user = None
        if rs is not None: 
            user = User(rs[0], rs[1], rs[2], rs[3])
        if reg_check and user is None : 
            msg = 'User ' + strjid + ' is not registered.'
        else:
            msg = ''
        return (user, msg)
    
    def _getUserDefaultLocation(self, c, user):
        location = None
        if user.getDefaultLocationId() is not None:
            rs = c.execute('SELECT location_id, user_id, name, long, lat FROM locations WHERE location_id=?', (user.getDefaultLocationId(),)).fetchone()
            if rs is not None:
                location = Location(rs[0], rs[1], rs[2], rs[3], rs[4])
        return location

    def _getAnyUserLocation(self, c, user):
        rs = c.execute('SELECT location_id, user_id, name, long, lat FROM locations WHERE user_id=?', (user.getUserId(),)).fetchone()
        location = None
        if rs is not None:
            location = Location(rs[0], rs[1], rs[2], rs[3], rs[5])
        return location

    def _getObserver(self, jid):
        observer = None
        with MasterDBConnection() as c:
            user, _ = self._getUser(c, jid, reg_check=False)
            if user is not None:
                loc = self._getUserDefaultLocation(c, user)
                if loc is None:
                    loc = self._getAnyUserLocation(c, user)
                if loc is not None:
                    observer = ephem.Observer()
                    observer.long, observer.lat = loc.getLonAsSexigesimal(), str(loc.getLatAsSexigesimal()) 
                    observer.elevation = 0  
        if observer is None:
            observer = self._obsr_default
        return observer
    
    def _getObserverCopy(self, jid):  
        co = self._getObserver(jid)
        obsrv =  ephem.Observer()
        obsrv.long, obsrv.lat, obsrv.elevation = co.long, co.lat, co.elevation
        return obsrv

    def _getObserverStrCoord(self, jid):
        observer = self._getObserver(jid)
        lon = observer.long / math.pi * 180.0
        lat = observer.lat / math.pi * 180.0
        return "{0:.3f}".format(lon), "{0:.3f}".format(lat)
