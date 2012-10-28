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
        return self.getName() + '['+ str(self.getLng()) + ','+ str(self.getLat()) + ']'