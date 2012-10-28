class Location(object):
    ''' Location class
    '''
    def __init__(self, location_id, user_id, name, lng, lat):
        self._location_id = location_id
        self._user_id = user_id
        self._name = name
        self._lng = lng
        self._lat = lat
    
    def getLocationId(self):
        ''' Return Location ID
        '''
        return self._location_id

    def getUserId(self):
        ''' Return user id
        '''
        return self._user_id

    def getName(self):
        ''' Return name of location
        '''
        return self._name

    def getLat(self):
        ''' Return latitude in degrees  
        '''
        return self._lat

    def getLng(self):
        ''' Return longitude in degrees  
        '''
        return self._lng
    
    def getInfo(self):
        return self.getName() + ' [ '+ str(self.getLng()) + ', '+ str(self.getLat()) + ' ]'
    
    @staticmethod
    def getLocationById(c, location_id):
        loc = None
        rs = c.execute('SELECT location_id, user_id, name, long, lat FROM locations WHERE location_id=?', (location_id,)).fetchone()
        if rs is not None:
            loc = Location(rs[0], rs[1], rs[2], rs[3], rs[4])
        return loc
    
    @staticmethod
    def getUserLocationByName(c, user_id, loc_name):
        rs = c.execute("SELECT location_id, user_id, name, long, lat FROM locations WHERE user_id=? AND name=?", (user_id, loc_name)).fetchone()
        if rs is not None:
            loc = rs is not None and Location(rs[0], rs[1], rs[2], rs[3], rs[4]) or None
        else:
            loc = None
        return loc

    @staticmethod
    def getAnyUserLocation(c, user_id):
        rs = c.execute('SELECT location_id, user_id, name, long, lat FROM locations WHERE user_id=?', (user_id,)).fetchone()
        location = None
        if rs is not None:
            location = Location(rs[0], rs[1], rs[2], rs[3], rs[4])
        return location
