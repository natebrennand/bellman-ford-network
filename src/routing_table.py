
import json

RT_UPDATE = "RT_UPDATE"

class RoutingTable(object):

    def __init__(self, name, neighbor_list):
        self.table = {} # from --> to --> [cost, first step]
        self.name = name
        self.table[name] = {}
        self.table[name][name] = [0, name]

        for neighbor in neighbor_list:
            self.table[name][neighbor.name()] = [neighbor.cost, name]
            self.table[neighbor.name()] = {}
            for x in neighbor_list:
                self.table[neighbor.name()][x.name()] = [float('inf'), 'N/A']
            self.table[neighbor.name()][neighbor.name()] = [0, neighbor.name()]


    def update(self, packet):
        # see transmit_str() for format
        neighbor_name = packet['name']
        neighbor_vector = packet['data']
        self.table[neighbor_name] = neighbor_vector
        return self.__recompute()

    def __recompute(self):
        """ Re-calculates everything, returns the packet format if changes
            are made
        """
        changes = False
        # iterate through all neigboring nodes
        for dest, cost in self.table[self.name].iteritems():
            # find all possible costs
            possible_costs = []
            for n_name, n_cost in self.table[self.name].iteritems():
                possible_costs.append([n_cost + self.table[n_name][dest], n_name])
            # assign the smallest one
            self.table[self.name][dest] = min(*possible_costs)
            if self.table[self.name][dest] != cost:
                changes = True
        if changes:
            return self.transmit_str()
        return None

    def transmit_str(self):
        return json.dumps({
            "type": RT_UPDATE,
            "name": self.name,
            "data": self.table[self.name]
        })

    def __str__(self):
        rt = ""
        for client, cost in self.table[self.name]:
            rt += "Destination = {}, Cost = {}, Link = ({})\n".format(
                    client, cost, 




