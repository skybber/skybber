from location import Location

class User(object):
    """ User class
    """
    
    def __init__(self, user_id, jid, profile_description, default_location_id):
        self._user_id = user_id
        self._jid = jid
        self._profile_description = profile_description
        self._default_location_id = default_location_id
    
    def getUserId(self):
        return self._user_id
    
    def getJID(self):
        return self._jid
    
    def getProfileDescription(self):
        return self._profile_description
    
    def getDefaultLocationId(self):
        return self._default_location_id
    
    def getDefaultLocation(self, c):
        return Location.getLocationById(c, self.getDefaultLocationId())
    
    def getLocationByName(self, c, loc_name):
        rs = c.execute('SELECT location_id, user_id, name, long, lat FROM locations WHERE user_id=? AND name=?', (self.getUserId(), loc_name)).fetchone()
        if rs is not None:
            loc = rs is not None and Location(rs[0], rs[1], rs[2], rs[3], rs[4]) or None
        else:
            loc = None
        return loc

    def setDefaultLocation(self, c, location):
        c.execute('UPDATE users SET default_location_id=? WHERE user_id=?', (location.getLocationId(), self.getUserId(),))

    def getUserLocationList(self, c, size = None):
        rs = c.execute('SELECT location_id, user_id, name, long, lat FROM locations WHERE user_id=?', (self.getUserId(), ))
        result = ()
        if size is None or size > 0:
            for rsloc in rs:
                loc = Location(rsloc[0], rsloc[1], rsloc[2], rsloc[3], rsloc[4])
                result += (loc, )
                if size is not None and len(result) >= size:
                    break;
        if size == 1:
            if len(result) == 0:
                result = None
            else:
                result = result[0]
        return result
    
    def createLocation(self, c, loc_name, lng, lat):
        c.execute('INSERT INTO locations(user_id, name, long, lat) VALUES (?,?,?,?)', (self.getUserId(), loc_name, lng, lat))
        return self.getLocationByName(c, loc_name)
    
    def delete(self, c):
        c.execute('DELETE FROM users WHERE user_id=?', (self.getUserId(), ))
        c.execute('DELETE FROM locations WHERE user_id=?', (self.getUserId(), ))

    @staticmethod
    def createUser(c, strjid):
        c.execute('INSERT INTO users(jid, descr) VALUES ( ?, ? )', (strjid, 'description'))
        return User.getUserbyJID(c, strjid)

    @staticmethod
    def getUserbyJID(c, strjid):
        rs = c.execute('SELECT user_id, jid, descr, default_location_id FROM users WHERE jid=?', (strjid, )).fetchone()
        user = None
        if rs is not None: 
            user = User(rs[0], rs[1], rs[2], rs[3])
        return user
