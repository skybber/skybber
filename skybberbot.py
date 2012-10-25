#!/usr/bin/env python
# coding: utf-8

from jabberbot import botcmd
from satellitepass import SatellitePasses
from iriflares import IridiumFlares
from mucjabberbot import MUCJabberBot
import sqlite3
import datetime
import urllib2
import math
import ephem
import utils
from user import User

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
        self._obsr_default.lat, self._obsr_default.long = '50.76111', '15.05728'
        self._obsr_default.elevation = 400  

    def _getObserver(self, jid):
        obsrv = None
        with MasterDBConnection() as c:
            user, _ = self._getRegisteredUser(c, jid, reg_check=False)
            
            if user is not None:
                loc = c.execute('SELECT lat, long FROM locations WHERE user_id=?', (user.getUserId(),)).fetchone()
                if loc is not None:
                    obsrv = ephem.Observer()
                    obsrv.lat, obsrv.long = str(loc[0]), str(loc[1]) 
                    obsrv.elevation = 0  

        if obsrv is None:
            obsrv = self._obsr_default
        return obsrv  
    
    def _getObserverCopy(self, jid):  
        co = self._getObserver(jid)
        obsrv =  ephem.Observer()
        obsrv.lat, obsrv.long, obsrv.elevation = co.lat, co.long, co.elevation
        return obsrv
    
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

        req = urllib2.Request('http://api.uhaapi.com/satellites/iridium/flares?' + \
                              'lat=' + + '&lng=' + , None, {})
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

        req = urllib2.Request('http://api.uhaapi.com/satellites/' + satid + '/passes?' + \
                              'lat=' + + '&lng=' + , None, {})
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
    def register(self, mess, args):
        ''' registers user into skybber  
        '''
        with MasterDBConnection() as c:
            str_jid = mess.getFrom().getStripped()
            user, _ = self._getRegisteredUser(c, str_jid, reg_check=False)
            if user is not None:
                reply = 'User ' + str_jid + ' is already registered !' 
            else:
                c.execute('INSERT INTO users(jid, descr) VALUES ( ?, ? )', (mess.getFrom().getStripped(), 'description'))
                reply = 'User ' + str_jid + ' is registered.' 
        
        self.send_simple_reply(mess, reply)

    @botcmd 
    def unregister(self, mess, args):
        ''' unregister user from skybber  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getRegisteredUser(c, mess.getFrom().getStripped())
            if user is not None:
                c.execute('DELETE FROM users WHERE jid=?', (user.getJID(), ))
                c.execute('DELETE FROM locations WHERE user_id=?', (user.getUserId(), ))
                reply = 'User ' + user.getJID() + ' was unregistered.' 
        
        self.send_simple_reply(mess, reply)
        

    @botcmd 
    def profile(self, mess, args):
        ''' Shows user profile  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getRegisteredUser(c, mess.getFrom().getStripped())
            if user is not None:
                reply = 'JID :' + user.getJID() + ' profile info: ' + user.getProfileDescription() 
        self.send_simple_reply(mess, reply)
            
    @botcmd 
    def addloc(self, mess, args):
        ''' add user location  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getRegisteredUser(c, mess.getFrom().getStripped())
            if user is not None:
                pargs = utils.parseArgs(args)
                if 'name' in pargs and 'lat' in pargs and 'long' in pargs:
                    c.execute('INSERT INTO locations(user_id, name, lat, long) VALUES (?,?,?,?)', \
                              (user.getUserId(), pargs['name'], float(pargs['lat']), float(pargs['long'])))
                    reply = 'Location added. (' + pargs['name'] + '[' + pargs['lat'] + ',' + pargs['long'] + '])'  
                else:
                    reply = 'Invalid command option. Usage: addloc name=<location name> long=<longitude> lat=<latitude>' 

        self.send_simple_reply(mess, reply)

    @botcmd 
    def rmloc(self, mess, args):
        ''' removes user location.  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getRegisteredUser(c, mess.getFrom().getStripped())
            if user is not None:
                pargs = utils.parseArgs(args)
                if 'name' in pargs:
                    c.execute('DELETE FROM locations WHERE user_id=? AND name=?', (user.getUserId(), pargs['name']))
                    reply = 'Location "' + pargs['name'] + '" was removed.'  
                else:
                    reply = 'Invalid command option. Usage: rmloc name=NAME' 

        self.send_simple_reply(mess, reply)

    @botcmd 
    def lsloc(self, mess, args):
        ''' list user locations  
        '''
        with MasterDBConnection() as c:
            user, reply = self._getRegisteredUser(c, mess.getFrom().getStripped())
            if user is not None:
                rs = c.execute("SELECT name, lat, long FROM locations WHERE user_id=?", (user.getUserId(), ))
                reply = 'User locations : \n'
                for loc in rs:
                    reply += loc[0] + ' [' + str(loc[1]) + ', ' + str(loc[2]) + ']\n' 
        self.send_simple_reply(mess, reply)

    def _getRegisteredUser(self, c, strjid, reg_check=True):
        rs = c.execute("SELECT user_id, jid, descr FROM users WHERE jid=?", (strjid, )).fetchone()
        user = None
        if rs is not None: 
            user = User(rs[0], rs[1], rs[2])
        if reg_check and user is None : 
            msg = 'User ' + strjid + ' is not registered.'
        else:
            msg = ''
        return (user, msg)
            
