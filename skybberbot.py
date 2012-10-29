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

from iriflares import IridiumFlares
from jabberbot import botcmd
from mucjabberbot import MUCJabberBot
from satellitepass import SatellitePasses
from user import User
import datetime
import ephem
import math
import re
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
    
    MAX_USER_LOCATIONS = 10
    
    def __init__(self, *args, **kwargs):
        MUCJabberBot.__init__(self, *args, **kwargs)
        self._obsr_default = ephem.Observer()
        self._obsr_default.long, self._obsr_default.lat = '15.05728', '50.76111'
        self._obsr_default.elevation = 400  
        self._arg_re = re.compile('[ \t]+')

    def top_of_help_message(self):
        return '\n        This is astronomical jabber bot - SKYBBER!\n'

    @botcmd
    def satinfo(self, mess, args):
        '''satinfo - information about satellite identified by satellite id
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
        '''satpass - shows satellite passes identified by satellite id
        '''
        if args is None or len(args) == 0:
            return '<b>Usage:</b> satpass satellite ID'

        try:
            satid = int(args)
            return self._satteliteRequest(mess, args, str(satid))
        except ValueError as e:
            return '<b>Usage:</b> satpass satellite ID'
            print e

    @botcmd
    def iss(self, mess, args):
        '''iss - shows ISS passes
        '''
        return self._satteliteRequest(mess, args, '25544')

    @botcmd
    def iri(self, mess, args):
        '''iri - shows Iridium flares
        '''
        opener = urllib2.build_opener()
        opener.addheaders = [
            ('Accept', 'application/xml'), # Change this to applicaiton/xml to get an XML response
        ]
        
        lng, lat = self._getObserverStrCoord(mess.getFrom().getStripped())
        req = urllib2.Request('http://api.uhaapi.com/satellites/iridium/flares?lat=' + lat + '&lng=' + lng, None, {})
        try:
            reply = opener.open(req).read()
            iflares = IridiumFlares()
            iflares.parseFromXml(reply)
            fmt_txt = iflares.format() 
            self.send_simple_reply(mess, fmt_txt)
        except urllib2.URLError as e:
            self.send_simple_reply(mess, 'Service disconnected.')
            print e
    
    @botcmd
    def tw(self, mess, args):
        '''tw - shows begin/end of current twilight  
        '''
        body = ephem.Sun()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '-18.0', datetime.datetime.utcnow())
        reply = 'v' + utils.formatLocalTime(next_setting) + '  -  ^' + utils.formatLocalTime(next_rising) 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def sun(self, mess, args):
        '''sun - shows sun info  
        '''
        body = ephem.Sun()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = 'v' + utils.formatLocalTime(next_setting) + '  -  ^' + utils.formatLocalTime(next_rising) 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def moon(self, mess, args):
        '''moon - shows Moon ephemeris  
        '''
        body = ephem.Moon()
        body.compute()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = '^' + utils.formatLocalTime(next_rising) + ' -  v' + utils.formatLocalTime(next_setting)
        reply += '  Phase ' +  ("%0.1f" % body.phase) 
        reply += '  [ ' +  ephem.constellation(body)[1] + ' ]' 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def mer(self, mess, args):
        '''mer - shows Mercury ephemeris  
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
        reply += '  Elong ' + ("%0.2f" % elong)
        reply += '  [ ' +  ephem.constellation(body)[1] + ' ]' 
        self.send_simple_reply(mess, reply)
    
    @botcmd 
    def ven(self, mess, args):
        '''ven - shows Venus ephemeris  
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
        reply += '   Elong ' + ("%0.2f" % elong)
        reply += '  [ ' +  ephem.constellation(body)[1] + ' ]' 
        self.send_simple_reply(mess, reply)

    @botcmd 
    def mar(self, mess, args):
        '''mar - shows Mars ephemeris  
        '''
        body = ephem.Mars()
        body.compute()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = utils.formatRiseSet(body, next_rising, next_setting)
        self.send_simple_reply(mess, reply)

    @botcmd 
    def jup(self, mess, args):
        '''jup - shows Jupiter ephemeris  
        '''
        body = ephem.Jupiter()
        body.compute()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = utils.formatRiseSet(body, next_rising, next_setting)
        self.send_simple_reply(mess, reply)

    @botcmd 
    def sat(self, mess, args):
        '''sat - shows Saturn ephemeris  
        '''
        body = ephem.Saturn()
        body.compute()
        next_rising, next_setting = self._getNextRiseSetting(mess.getFrom().getStripped(), body, '0.0', datetime.datetime.utcnow())
        reply = utils.formatRiseSet(body, next_rising, next_setting)
        self.send_simple_reply(mess, reply)

    @botcmd 
    def reg(self, mess, args):
        '''reg - registers user into skybber  
        '''
        with MasterDBConnection() as c:
            str_jid = mess.getFrom().getStripped()
            user, _ = self._getUser(c, str_jid, reg_check=False)
            if user is not None:
                reply = 'User ' + user.getJID() + ' is already registered !' 
            else:
                user = User.createUser(c, mess.getFrom().getStripped())
                reply = 'User ' + user.getJID() + ' is registered.' 
        
        self.send_simple_reply(mess, reply)

    @botcmd(allowed_roles={'registered'}) 
    def unregister(self, mess, args):
        '''unregister - unregister user from skybber  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                user.delete(c)
                reply = 'User ' + user.getJID() + ' was unregistered.' 
        
        self.send_simple_reply(mess, reply)
        

    @botcmd(allowed_roles={'registered'})
    def prof(self, mess, args):
        '''prof - shows user profile  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                reply = '\nJID :' + user.getJID() + '\nDescription: ' + user.getProfileDescription() + '\nDefault location: '
                loc = user.getDefaultLocation(c)
                if loc is None:
                    reply += 'undefined.'
                else:
                    reply += loc.getName()
        self.send_simple_reply(mess, reply)
            
    @botcmd(allowed_roles={'registered'}) 
    def addloc(self, mess, args):
        '''addloc <name> <longitude> <latitude> - adds user location. 
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                pargs = self._arg_re.split(args.strip())
                if len(pargs) == 3: 
                    if utils.is_number(pargs[1]) and utils.is_number(pargs[2]):
                        loc = user.getLocationByName(c, pargs[0])
                        if loc is None:
                            user_locations = user.getUserLocationList(c)
                            if len(user_locations) < self.MAX_USER_LOCATIONS:
                                loc = user.createLocation(c, pargs[0], float(pargs[1]), float(pargs[2]))
                                reply = 'Location "' + loc.getInfo() + '" added.'
                                # set default location if it is a first one 
                                if len(user_locations) == 0:
                                    user.setDefaultLocation(c, loc)
                                    reply += ' Location set as default location.'
                            else:
                                reply = 'Add location failed. Number of user locations exceeded limit ' + self.MAX_USER_LOCATIONS 
                        else:
                            reply = 'Location "' + loc.getInfo() + '" already exists.' 
                    else:
                        reply = 'Invalid option type. Number expected.' 
                else:
                    reply = 'Invalid number of options.' 

        self.send_simple_reply(mess, reply)

    @botcmd(allowed_roles={'registered'})
    def rmloc(self, mess, args):
        '''rmloc <name> - removes location.  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                pargs = self._arg_re.split(args.strip())
                if len(pargs) == 1:
                    loc = user.getLocationByName(c, pargs[0])
                    loc.delete(c)
                    reply = 'Location "' + loc.getInfo() + '" was removed.'  
                else:
                    reply = 'Invalid number of options.' 

        self.send_simple_reply(mess, reply)

    @botcmd(allowed_roles={'registered'}) 
    def loc(self, mess, args):
        '''loc <name> - set the location as the new default location .  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                pargs = self._arg_re.split(args.strip())
                if len(pargs) == 1:
                    loc = user.getLocationByName(c, pargs[0])
                    if loc is not None:
                        user.setDefaultLocation(c, loc)
                        reply = loc.getInfo() + '   is your default location now.'  
                    else:
                        reply = 'Unknown location: ' + args
                else: 
                    reply = 'Invalid number of options.' 
        self.send_simple_reply(mess, reply)
        

    @botcmd(allowed_roles={'registered'})
    def lsloc(self, mess, args):
        '''lsloc - shows the list of locations  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getUser(c, mess.getFrom().getStripped())
            if user is not None:
                def_loc = user.getDefaultLocation(c)
                reply = '\nUser locations : \n'
                for loc in user.getUserLocationList(c):
                    reply += loc.getInfo()
                    if def_loc is not None and def_loc.getLocationId() == loc.getLocationId():
                        reply += '  *'
                    reply += '\n'  
        self.send_simple_reply(mess, reply)
        
    def _satteliteRequest(self, mess, args, satid):
        ''' TODO:
        '''
        opener = urllib2.build_opener()
        opener.addheaders = [
            ('Accept', 'application/xml'), # Change this to applicaiton/xml to get an XML response
        ]

        lng, lat = self._getObserverStrCoord(mess.getFrom().getStripped())

        req = urllib2.Request('http://api.uhaapi.com/satellites/' + satid + '/passes?lat=' + lat + '&lng=' + lng, None, {})
        try:
            reply = opener.open(req).read()
            sp = SatellitePasses()
            sp.parseFromXml(reply)
            fmt_txt = sp.format() 
            self.send_simple_reply(mess, fmt_txt)
        except urllib2.URLError as e:
            self.send_simple_reply(mess, 'Service disconnected.')
            print e

    def _getNextRiseSetting(self, jid, body, horizon, dt):
        ''' TODO:
        '''
        observer = self._getObserverCopy(jid)
        observer.horizon = horizon
        observer.date = ephem.Date(dt) 
        next_rising = observer.next_rising(body)
        next_setting = observer.next_setting(body)
        return next_rising, next_setting 


    def _getUser(self, c, strjid, reg_check=True):
        ''' TODO:
        '''
        user = User.getUserbyJID(c, strjid)
        if reg_check and user is None : 
            msg = 'User ' + strjid + ' is not registered.'
        else:
            msg = ''
        return (user, msg)
    
    def _getObserver(self, jid, loc_name = None):
        '''Creates observer object initialized from location 
        
        1. It looks for location by location_name for given user(jid)
        2. if not exists  then it looks for user default location
        3. if not exists then returns first user location
        '''
        observer = None
        with MasterDBConnection() as c:
            user, _ = self._getUser(c, jid, reg_check=False)
            if user is not None:
                if loc_name is not None:
                    loc = user.getLocationByName(c, loc_name)
                    # TODO : return message if loc is None
                else:
                    loc = user.getDefaultLocation(c)
                    if loc is None:
                        loc = user.getUserLocationList(c, 1)
                    if loc is not None:
                        observer = ephem.Observer()
                        observer.long, observer.lat = utils.toradians(loc.getLng()), utils.toradians(loc.getLat()) 
                        observer.elevation = 0  
        if observer is None:
            observer = self._obsr_default
        return observer
    
    def _getObserverCopy(self, jid, loc_name = None):
        '''Returns copy of observer object
        '''  
        co = self._getObserver(jid, loc_name)
        obsrv =  ephem.Observer()
        obsrv.long, obsrv.lat, obsrv.elevation = co.long, co.lat, co.elevation
        return obsrv

    def _getObserverStrCoord(self, jid, loc_name = None):
        '''Gets observer's coordinations in string form 
        '''
        observer = self._getObserver(jid, loc_name)
        lng = utils.todegrees(observer.long)
        lat = utils.todegrees(observer.lat)
        return ("%0.3f" % lng), ("%0.3f" % lat)

    def check_role(self, allowed_roles, mess):
        '''checks if user from message heas enough rights for specified role
        '''
        permit = True
        if allowed_roles is not None:
            user_roles = self._getUserRoles(mess.getFrom().getStripped())
            if user_roles is None:
                permit = False
            else:
                permit = not user_roles.isdisjoint(allowed_roles) 
        return permit

    def _getUserRoles(self, jid):
        '''Returns list of user's roles
        '''
        with MasterDBConnection() as c:
            user, _ = self._getUser(c, jid, reg_check=False)
            if user is not None:
                return {'registered'}
        return None
