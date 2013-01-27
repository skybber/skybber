# coding: utf-8

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
import time 
import ephem
import math
import re
import sqlite3
import urllib2
import utils
from typedetector import TypeDetector
from location import Location

class CmdError(Exception):
    """ Help class for handling command arguments errors
    """
    def __init__(self, value):
        self.value = value
        def __str__(self):
            return repr(self.value)

class MasterDBConnection():
    """ Help class keeping DB connection
    """
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
    # MSG_HELP_TAIL = 'Type %(helpcommand)s <command name> to get more info about that specific command.'
    MSG_HELP_TAIL = ''
    MSG_HELP_UNDEFINED_COMMAND = 'Undefined command.'
    MSG_ERROR_OCCURRED = 'Unexpected error.'
    
    MSG_NO_ASTRONOMICAL_NIGHT = 'No astronomical night'
    MSG_FULL_ASTRONOMICAL_NIGHT = '24hrs astronomical night.'

    PING_FREQUENCY = 60  # Set to the number of seconds, e.g. 60.
    PING_TIMEOUT = 2  # Seconds to wait for a response.
    
    MAX_USER_LOCATIONS = 10
    
    RISET_OK = 0
    NEVER_RISING = 1
    NEVER_SETTING = 2
    
    def __init__(self, *args, **kwargs):
        MUCJabberBot.__init__(self, *args, **kwargs)
        self._obsr_default = ephem.Observer()
        self._obsr_default.long, self._obsr_default.lat = '15.05728', '50.76111'
        self._obsr_default.elevation = 400  
        self._arg_re = re.compile('[ \t]+')

    def top_of_help_message(self):
        """ Overridden from JabberBot
        """
        return '\n     This is astronomical jabber bot - SKYBBER!\n' + \
               '                      version 0.1 \n\n'
    def bottom_of_help_message(self):
        return u'\n\nDATE FORMATS: \n ‘YYYY-MM-DD’ or ‘YYYY/MM/DD  example: 2012/11/11’\n' + \
            u'LOCATION FORMATS: \n' + \
            u'   - angular, example : 14.86524 50.78461\n' + \
            u'   - geographic coordinations, example : 50°46\'1.105"N 15°3\'52.885"E\n' + \
            u'   - user location, example: prague' 

    @botcmd(thread=True)
    def satinfo(self, mess, args):
        """satinfo - information about satellite identified by satellite id
        """
        (satid, _, reply) = self._checkArgSatId(args)
        if satid is not None:
            try:
                opener = urllib2.build_opener()
                opener.addheaders = [
                    ('Accept', 'application/xml'), # Change this to applicaiton/xml to get an XML response
                ]
                
                req = urllib2.Request('http://api.uhaapi.com/satellites/' + str(satid) , None, {})
                reply = opener.open(req).read()
            except urllib2.URLError:
                reply = 'Service disconnected.'
        return reply
        
    @botcmd(thread=True)
    def satpass(self, mess, args):
        """satpass - show satellite passes identified by satellite id
        """
        (satid, next_args, reply) = self._checkArgSatId(args)
        if satid is not None:
            reply = self._satteliteRequest(mess, next_args, str(satid))
        else:
            reply = 'Satellite ID missing.'
        return reply

    @botcmd(thread=True)
    def iss(self, mess, args):
        """iss - show ISS passes
        """
        return self._satteliteRequest(mess, '', '25544')

    @botcmd(thread=True)
    def iri(self, mess, args):
        """iri - show Iridium flares
        """
        opener = urllib2.build_opener()
        opener.addheaders = [
            ('Accept', 'application/xml'), # Change this to applicaiton/xml to get an XML response
        ]
        
        jid, loc, _ = self._parseJidLocTime(mess, args)
        lng, lat = self._getObserverStrCoord(jid, loc)
        
        req = urllib2.Request('http://api.uhaapi.com/satellites/iridium/flares?lat=' + lat + '&lng=' + lng, None, {})
        
        iri_flares = IridiumFlares()
        
        try:
            xml_resp = opener.open(req).read()
            iri_flares.parseFromXml(xml_resp)
            reply = iri_flares.format() 
        except urllib2.URLError:
            reply = 'Service disconnected.'
        return reply
    
    @botcmd
    def tw(self, mess, args):
        """tw [date] [location]  - show begin/end of current twilight   
        """
        jid, loc, dt = self._parseJidLocTime(mess, args)

        # Set noon of if date is set
        if dt != None:
            dt = self._getNoonDateTimeFrom6To6ByDate(dt)

        next_rising, next_setting, riset = self._getNextRiseSetting(jid, ephem.Sun(), dt=dt, loc=loc, horizon='-18.0')
        
        if riset == SkybberBot.RISET_OK:
            reply = 'v' + utils.formatLocalTime(next_setting) + '  -  ^' + utils.formatLocalTime(next_rising)
        elif riset == SkybberBot.NEVER_SETTING:
            reply = SkybberBot.MSG_NO_ASTRONOMICAL_NIGHT
        else:
            reply = SkybberBot.MSG_FULL_ASTRONOMICAL_NIGHT
        return reply

    @botcmd
    def night(self, mess, args):
        """night [date] [location] - show the real night, taking into consideration the Moon rising/setting   
        """
        jid, loc, dt = self._parseJidLocTime(mess, args)

        # Set noon of if date is set
        if dt != None:
            dt = self._getNoonDateTimeFrom6To6ByDate(dt)

        next_sun_rising, next_sun_setting, riset_sun = self._getNextRiseSetting(jid, ephem.Sun(), dt=dt, loc=loc, horizon='-18.0')
        next_moon_rising, next_moon_setting, riset_moon = self._getNextRiseSetting(jid, ephem.Moon(), dt=dt, loc=loc)
        
        if riset_sun == SkybberBot.NEVER_SETTING:
            return SkybberBot.MSG_NO_ASTRONOMICAL_NIGHT
        
        full_night = False
        
        if riset_sun == SkybberBot.NEVER_SETTING:
            # TODO :
            # tw_start = start day time  
            # tw_end = end day time
            full_night = True
            pass 
        else:
            tw_start = next_sun_setting
            tw_end = next_sun_rising 

        tw_middle_end = None
        tw_middle_start = None 

        if riset_moon == SkybberBot.RISET_OK:
            if next_moon_rising < next_moon_setting:
                if next_moon_rising < next_sun_setting:  
                    if next_moon_setting > next_sun_setting:  
                        if next_moon_setting < next_sun_rising:
                            tw_start = next_moon_setting # MR - SS - MS - SR
                        else:
                            return SkybberBot.MSG_NO_ASTRONOMICAL_NIGHT # MR - SS - SR - MS
                    else:
                        pass  # MR - MS - SS - SR  
                else:
                    if next_moon_rising < next_sun_rising:
                        if next_moon_setting < next_sun_rising:
                            # SS - MR - MS - SR
                            tw_middle_end = next_moon_rising  
                            tw_middle_start = next_moon_rising 
                        else:
                            tw_end = next_moon_rising # SS - MR - SR - MS
                    else:
                        pass  # SS - SR - MR - MS
            else:
                if next_moon_setting < next_sun_setting:  
                    if next_moon_rising > next_sun_setting:  
                        if next_moon_rising < next_sun_rising:
                            tw_end = next_moon_rising # MS - SS - MR - SR
                        else:
                            pass # MS - SS - SR - MR
                    else:
                        return SkybberBot.MSG_NO_ASTRONOMICAL_NIGHT # MS - MR - SS - SR
                else:
                    if next_moon_setting < next_sun_rising:
                        if next_moon_rising < next_sun_rising:
                            # SS - MS - MR - SR
                            tw_start = next_moon_setting  
                            tw_end = next_moon_rising 
                        else:
                            tw_start = next_moon_setting # SS - MS - SR - MR
                    else:
                        return SkybberBot.MSG_NO_ASTRONOMICAL_NIGHT # SS - SR - MS - MR
        else:
            if riset_moon == SkybberBot.NEVER_SETTING:
                return SkybberBot.MSG_NO_ASTRONOMICAL_NIGHT
            elif full_night:
                return SkybberBot.MSG_FULL_ASTRONOMICAL_NIGHT
                
        if tw_middle_start is None:
            reply = 'v' + utils.formatLocalTime(tw_start) + '  -  ^' + utils.formatLocalTime(tw_end)
        else:
            reply = 'v' + utils.formatLocalTime(tw_start) + '  -  ^' + utils.formatLocalTime(tw_middle_end) + ' , ' + \
                    'v' + utils.formatLocalTime(tw_middle_end) + '  -  ^' + utils.formatLocalTime(tw_end)

        return reply
        
    @botcmd 
    def sun(self, mess, args):
        """sun [date] [location] - show sun info  
        """
        return self._doBodyEphem(mess, args, ephem.Sun(), with_constell_mag=False, rising_first=False)

    @botcmd 
    def moon(self, mess, args):
        """moon [date] [location] - show Moon ephemeris  
        """
        body = ephem.Moon()
        reply = self._doBodyEphem(mess, args, body, with_constell_mag=False)
        reply += '  Phase ' +  ("%0.1f" % body.phase) 
        reply += '  [ ' +  ephem.constellation(body)[1] + ' ]' 
        return reply

    @botcmd 
    def mer(self, mess, args):
        """mer [date] [location] - show Mercury ephemeris  
        """
        return self._doInnerBodyEphem(mess, args, ephem.Mercury())
    
    @botcmd 
    def ven(self, mess, args):
        """ven [date] [location] - show Venus ephemeris  
        """
        return self._doInnerBodyEphem(mess, args, ephem.Venus())

    @botcmd 
    def mar(self, mess, args):
        """mar [date] [location] - show Mars ephemeris  
        """
        return self._doBodyEphem(mess, args, ephem.Mars())

    @botcmd 
    def jup(self, mess, args):
        """jup [date] [location] - show Jupiter ephemeris  
        """
        return self._doBodyEphem(mess, args, ephem.Jupiter())

    @botcmd 
    def sat(self, mess, args):
        """sat [date] [location] - show Saturn ephemeris  
        """
        return self._doBodyEphem(mess, args, ephem.Saturn())

    @botcmd 
    def reg(self, mess, args):
        """reg - register user into skybber  
        """
        with MasterDBConnection() as c:
            str_jid = mess.getFrom().getStripped()
            user = self._getUser(c, str_jid, reg_check=False)
            if user is not None:
                raise CmdError('User ' + user.getJID() + ' is already registered !') 
            user = User.createUser(c, mess.getFrom().getStripped())
            reply = 'User ' + user.getJID() + ' is registered.' 
        
        return reply

    @botcmd(allowed_roles={'registered'}) 
    def unregister(self, mess, args):
        """unregister - unregister user from skybber  
        """
        with MasterDBConnection() as c:
            user = self._getUser(c, mess.getFrom().getStripped())
            user.delete(c)
            reply = 'User ' + user.getJID() + ' was unregistered.'
        
        return reply
        

    @botcmd(allowed_roles={'registered'})
    def prof(self, mess, args):
        """prof - show user profile  
        """
        with MasterDBConnection() as c:
            user = self._getUser(c, mess.getFrom().getStripped())
            reply = '\nJID :' + user.getJID() + '\nDescription: ' + user.getProfileDescription() + '\nDefault location: '
            loc = user.getDefaultLocation(c)
            if loc is None:
                reply += 'undefined.'
            else:
                reply += loc.getName()
        return reply
            
    @botcmd(allowed_roles={'registered'}) 
    def addloc(self, mess, args):
        """addloc <name> <longitude> <latitude> - add user location. 
        """
        with MasterDBConnection() as c:
            user = self._getUser(c, mess.getFrom().getStripped())
            pargs = self._arg_re.split(args.strip())
            if len(pargs) == 3: 
                reply = self._doAddLoc(c, user, pargs[0].strip(), pargs[1].strip(), pargs[2].strip())
            else:
                reply = 'Invalid number of arguments.' 
        return reply

    @botcmd(allowed_roles={'registered'})
    def rmloc(self, mess, args):
        """rmloc <name> - remove location.  
        """
        with MasterDBConnection() as c:
            user = self._getUser(c, mess.getFrom().getStripped())
            pargs = self._arg_re.split(args.strip())
            if len(pargs) == 1:
                loc = user.getLocationByName(c, pargs[0])
                loc.delete(c)
                reply = 'Location "' + loc.getInfo() + '" was removed.'  
            elif len(pargs) == 0:
                reply = 'Argument  - location name - expected.' 
            else:
                reply = 'Invalid number of arguments.' 

        return reply

    @botcmd(allowed_roles={'registered'}) 
    def loc(self, mess, args):
        """loc <name> - set the location as the new default location .  
        """
        with MasterDBConnection() as c:
            user = self._getUser(c, mess.getFrom().getStripped())
            pargs = self._arg_re.split(args.strip())
            if len(pargs) == 1:
                loc = user.getLocationByName(c, pargs[0])
                if loc is not None:
                    user.setDefaultLocation(c, loc)
                    reply = loc.getInfo() + '   is your default location now.'  
            elif len(pargs) == 0:
                reply = 'Argument  - location name - expected.' 
            else:
                reply = 'Invalid number of arguments.'
        return reply
        

    @botcmd(allowed_roles={'registered'})
    def lsloc(self, mess, args):
        """lsloc - show the list of locations  
        """
        with MasterDBConnection() as c:
            user = self._getUser(c, mess.getFrom().getStripped())
            def_loc = user.getDefaultLocation(c)
            reply = '\nUser locations : \n'
            for loc in user.getUserLocationList(c):
                reply += loc.getInfo()
                if def_loc is not None and def_loc.getLocationId() == loc.getLocationId():
                    reply += '  *'
                reply += '\n'  
        return reply
        
    def check_role(self, allowed_roles, mess):
        """Overridden from JabberBot 
           
        check if user from message heas enough rights for specified role
        """
        permit = True
        if allowed_roles is not None:
            user_roles = self._getUserRoles(mess.getFrom().getStripped())
            if user_roles is None:
                permit = False
            else:
                permit = not user_roles.isdisjoint(allowed_roles) 
        return permit

    def execute_command(self, mess, cmd, args):
        """ Overridden from JabberBot
        """
        try:
            reply = MUCJabberBot.execute_command(self, mess, cmd, args)
        except CmdError, e:
            reply = e.value
        return reply       

    def _satteliteRequest(self, mess, args, satid):
        """ TODO:
        """
        opener = urllib2.build_opener()
        opener.addheaders = [
            ('Accept', 'application/xml'), # Change this to applicaiton/xml to get an XML response
        ]

        jid, loc, _ = self._parseJidLocTime(mess, args)
        lng, lat = self._getObserverStrCoord(jid, loc)

        req = urllib2.Request('http://api.uhaapi.com/satellites/' + satid + '/passes?lat=' + lat + '&lng=' + lng, None, {})
        try:
            reply = opener.open(req).read()
            sp = SatellitePasses()
            sp.parseFromXml(reply)
            return sp.format() 
        except urllib2.URLError:
            return 'Service disconnected.'

    def _getUser(self, c, strjid, reg_check=True):
        """ Return registered user 
        """
        user = User.getUserbyJID(c, strjid)
        if reg_check and user is None : 
            raise CmdError('User ' + strjid + ' is not registered.')
        return user
    
    def _getObserverByName(self, jid, loc_name = None):
        """Create observer object initialized from location 
        
        1. It looks for location by location_name for given user(jid)
        2. if not exists  then it looks for user default location
        3. if not exists then returns first user location
        """
        observer = None
        with MasterDBConnection() as c:
            user = self._getUser(c, jid, reg_check=False)
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
    
    def _getObserver(self, jid, loc):
        """Return copy of observer object
        """
        obsrv =  ephem.Observer()
        
        if loc is not None:
            if loc.getName() is not None:
                co = self._getObserverByName(jid, loc_name=loc.getName())
                obsrv.long, obsrv.lat, obsrv.elevation = co.long, co.lat, co.elevation
            else:
                obsrv.long, obsrv.lat = loc.getLng(), loc.getLat()
        else: 
            co = self._getObserverByName(jid)
            obsrv.long, obsrv.lat, obsrv.elevation = co.long, co.lat, co.elevation
                 
        return obsrv

    def _getObserverStrCoord(self, jid, loc):
        """Get observer's coordinations in string form 
        """
        observer = self._getObserver(jid, loc)
        lng = utils.todegrees(observer.long)
        lat = utils.todegrees(observer.lat)
        return ("%0.3f" % lng), ("%0.3f" % lat)

    def _checkArgSatId(self, args):
        satid = None
        next_args = None
        pargs = self._arg_re.split(args.strip())
        if pargs is None or len(pargs) == 0:
            reply = 'Argument expected. Please specify satellite ID.'
        else:
            try:
                satid = int(pargs[0])
                reply = None
                next_args = args[len(pargs[0]):]
            except ValueError:
                reply = 'Argument expected. Please specify satellite ID.'
        return (satid, next_args, reply)

    def _getUserRoles(self, jid):
        """Return list of user's roles
        """
        with MasterDBConnection() as c:
            user = self._getUser(c, jid, reg_check=False)
            if user is not None:
                return {'registered'}
        return None

    def _doAddLoc(self, c, user, loc_name, sval1, sval2):
        """ Add location to list of locations. It reads geographic position in angle or geo format
        """

        val1 = TypeDetector(sval1)
        val2 = TypeDetector(sval2)
        
        lng = 0.0 
        lat = 0.0 
        
        if val1.getType() == TypeDetector.FLOAT:
            if val2.getType() == TypeDetector.FLOAT:
                lng = val1.getTypeValue()
                lat = val2.getTypeValue()
            else:
                return 'Invalid argument: "' + sval2 + '".  Number is expected.'
        elif val1.getType() == TypeDetector.LOCATION_LONG:
            if val2.getType() == TypeDetector.LOCATION_LAT:
                lng = val1.getTypeValue()
                lat = val2.getTypeValue()
            else:
                return 'Invalid argument: "' + sval2 + u'". Latitude expected. Example: 15°3\'53.856"E' 
        elif val1.getType() == TypeDetector.LOCATION_LAT:
            if val2.getType() == TypeDetector.LOCATION_LONG:
                lat = val1.getTypeValue()
                lng = val2.getTypeValue()
            else:
                return 'Invalid argument: "' + sval2 + u'". Longitude expected. Example: 50°46\'1.655"N'
        else:
            return 'Invalid format of argument value: "' + sval1 + '". Use help for .'
            
        loc = user.getLocationByName(c, loc_name)

        if loc is None:
            user_locations = user.getUserLocationList(c)
            if len(user_locations) < self.MAX_USER_LOCATIONS:
                loc = user.createLocation(c, loc_name, lng, lat)
                reply = 'Location "' + loc.getInfo() + '" added.'
                # set default location if it is a first one 
                if len(user_locations) == 0:
                    user.setDefaultLocation(c, loc)
                    reply += ' Location set as default location.'
            else:
                reply = 'Add location failed. Number of user locations exceeded limit ' + self.MAX_USER_LOCATIONS 
        else:
            reply = 'Location "' + loc.getInfo() + '" already exists.'
        
        return reply 

    def _fmtRiSetFailMsg(self, body, riset):
        result = body.name + ' ' 
        if riset == SkybberBot.NEVER_RISING:
            result += 'never rising.'
        else:
            result += 'never setting.'

    def _doInnerBodyEphem(self, mess, args, body, with_constell_mag=True):
        body.compute()

        elong = math.degrees(body.elong)
        
        jid, loc, dt = self._parseJidLocTime(mess, args)
        next_rising, next_setting, riset = self._getNextRiseSetting(jid, body, dt=dt, loc=loc, horizon='0.0')

        if riset == SkybberBot.RISET_OK:
            if elong > 0.0:
                result = 'v' + utils.formatLocalTime(next_setting)
            else:
                result = '^' + utils.formatLocalTime(next_rising)
        else:
            result = self._fmtRiSetFailMsg(body, riset)
        
        result += '  Elong ' + ("%0.2f" % elong)

        if with_constell_mag:
            result += '  ' + str(body.mag) + 'm'
            result += '  [ ' +  ephem.constellation(body)[1] + ' ]'
        return result 

    def _doBodyEphem(self, mess, args, body, with_constell_mag=True, rising_first=True):
        """ Return next rise/setting for specified body.
        """
        body.compute()
        
        jid, loc, dt = self._parseJidLocTime(mess, args)
        next_rising, next_setting, riset = self._getNextRiseSetting(jid, body, dt=dt, loc=loc, horizon='0.0')
        
        if riset == SkybberBot.RISET_OK:
            if rising_first:
                result = '^' + utils.formatLocalTime(next_rising) + '  v' + utils.formatLocalTime(next_setting)
            else:
                result = 'v' + utils.formatLocalTime(next_setting) + '  ^' + utils.formatLocalTime(next_rising)
        else:
            result = self._fmtRiSetFailMsg(body, riset) 
        if with_constell_mag: 
            result += '  ' + str(body.mag) + 'm'
            result += '  [ ' +  ephem.constellation(body)[1] + ' ]' 
        return result

    def _getNextRiseSetting(self, jid, body, loc=None, dt=None, horizon = '0.0'):
        """ Return next rising/setting time for given body, horizont and date 
        """
        observer = self._getObserver(jid, loc)
        observer.horizon = horizon
        
        if dt == None:
            dt = self._getNoonDateTimeFrom6To6()
        
        observer.date = ephem.Date(dt)

        try: 
            next_rising = observer.next_rising(body)
            next_setting = observer.next_setting(body)
            riset = SkybberBot.RISET_OK
        except ephem.NeverUpError:
            next_rising = None
            next_setting = None
            riset = SkybberBot.NEVER_RISING
        except ephem.AlwaysUpError:
            next_rising = None
            next_setting = None
            riset = SkybberBot.NEVER_SETTING
        
        return (next_rising, next_setting, riset) 

    def _getNoonDateTimeFrom6To6(self):
        """ Return noon of day beetween 06:00 of that day to next day 06:00 
        """
        date = datetime.date.today()
        if datetime.datetime.now().hour < 6:
            date -= datetime.timedelta(1)

        dt = datetime.datetime.combine(datetime.date.today(), datetime.time(12,0)) 
        dt = dt + datetime.timedelta(0, time.timezone)
        
        return dt

    def _getNoonDateTimeFrom6To6ByDate(self, date):
        """ Return noon of day beetween 06:00 of that day to next day 06:00 
        """
        dt = datetime.datetime.combine(date, datetime.time(12,0)) 
        dt = dt + datetime.timedelta(0, time.timezone)
        
        return dt

    def _parseJidLocTime(self, mess, args, parse_date = True):
        jid = mess.getFrom().getStripped()
        
        args = args.strip()
        
        if args is None or len(args) == 0:
            return (jid, None, None) 

        loc = None
        dt = None
        lng = None
        lat = None
        loc_name = None

        pargs = self._arg_re.split(args.strip())
        
        if pargs is not None:
            for arg in pargs:
                parsed_arg = TypeDetector(arg)
                if parse_date and parsed_arg.getType() == TypeDetector.DATE:
                    if dt is not None:
                        raise CmdError('Invalid double date argument: ' + arg)
                    dt = parsed_arg.getTypeValue()
                elif parsed_arg.getType() == TypeDetector.LOCATION_LONG:
                    if lng is not None:
                        raise CmdError('Invalid double longitude argument: ' + arg)
                    lng = parsed_arg.getTypeValue()
                elif parsed_arg.getType() == TypeDetector.LOCATION_LAT:
                    if lat is not None:
                        raise CmdError('Invalid double latitude argument: ' + arg)
                    lat = parsed_arg.getTypeValue()
                elif parsed_arg.getType() == TypeDetector.STRING:
                    if loc_name is not None:
                        raise CmdError('Invalid double location name argument: ' + arg)
                    loc_name = parsed_arg.getValue()
                else:
                    raise CmdError('Invalid argument: ' + arg)
        
            if (lng is not None or lat is not None) and loc_name is not None:
                raise CmdError('Invalid arguments. Please specify only one of longitude/latitude or location name.')
            if lng is not None and lat is None:
                raise CmdError('Invalid argument. Latitude missing.')
            if lng is None and lat is not None:
                raise CmdError('Invalid argument. Latitude missing.')
            if lng is not None:
                loc = Location(None, None, None, lng, lat)
            elif loc_name is not None:
                loc = Location(None, None, loc_name, None, None)
                  
        return (jid, loc, dt)
