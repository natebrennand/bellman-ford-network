
class Node(object):

    def __init__(self, ip, port, weight):
        self.ip = ip
        self.port = port
        self.weight = weight

    def update_rt(self, rt_str, conn):
        conn.sendto(rt_str, (self.ip, self.port))
        print 'sent rt to ',  self.ip, self.port
    
    def message(self, msg, conn):
        conn.sendto(msg, (self.ip, self.port))

    def name(self):
        return "{}:{}".format(self.ip, self.port)

    def forward_file(self, f, dest):
        pass
