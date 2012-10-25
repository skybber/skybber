
class User(object):
    def __init__(self, user_id, jid, profile_description):
        self.user_id = user_id
        self.jid = jid
        self.profile_description = profile_description
    
    def getUserId(self):
        return self.user_id
    
    def getJID(self):
        return self.jid
    
    def getProfileDescription(self):
        return self.profile_description