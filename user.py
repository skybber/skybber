class User(object):
    ''' User class
    '''
    
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

    @staticmethod
    def getUserbyJID(c, strjid):
        rs = c.execute("SELECT user_id, jid, descr, default_location_id FROM users WHERE jid=?", (strjid, )).fetchone()
        user = None
        if rs is not None: 
            user = User(rs[0], rs[1], rs[2], rs[3])
        return user
