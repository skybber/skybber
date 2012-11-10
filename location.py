class Location(object):
    """ Location class
    """
    def __init__(self, location_id, user_id, name, lng, lat):
        self._location_id = location_id
        self._user_id = user_id
        self._name = name
        self._lng = lng
        self._lat = lat
    
    def getLocationId(self):
        """ Return Location ID
        """
        return self._location_id

    def getUserId(self):
        """ Return user id
        """
        return self._user_id

    def getLat(self):
        """ Return latitude in degrees  
        """
        return self._lat

    def getLng(self):
        """ Return longitude in degrees  
        """
        return self._lng

    def getName(self):
        """ Return name of location
        """
        return self._name

    def getInfo(self):
        return self.getName() + ' [ '+ "%0.5f" % self.getLng() + ', '+ "%0.5f" % self.getLat() + ' ]'
    
    def delete(self, c):
        c.execute('DELETE FROM locations WHERE location_id=?', (self.getLocationId(), ))

    @staticmethod
    def getLocationById(c, location_id):
        loc = None
        rs = c.execute('SELECT location_id, user_id, name, long, lat FROM locations WHERE location_id=?', (location_id,)).fetchone()
        if rs is not None:
            loc = Location(rs[0], rs[1], rs[2], rs[3], rs[4])
        return loc
    
