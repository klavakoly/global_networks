class Authorization:

    def __init__(self, users):
        self.users = users[:]

    def __len__(self):
        return len(self.users)

    def __repr__(self):
        return f'< Authorization {self.users} >'


    def isAuthorized(self, user, password):
        for cu, cp in self.users:
            if cu == user and cp == password:
                return True
            
        return False
    

def defaultAuthorization():
    return Authorization([('admin','admin'), ('Lera','12345')])


