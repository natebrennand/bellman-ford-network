
import json

RT_UPDATE = "ROUTE_UPDATE"
RT_LINKUP = "ROUTE_LINKUP"
RT_LINKDOWN = "ROUTE_LINKDOWN"

class RoutingTable(object):

    def __init__(self,neighbor_list, source):
        self.table = {} # from --> to --> [cost, first step]
        self.src_node = source.name()
        self.ip = source.ip
        self.port = source.port

        # initialize table for every node
        self.table[self.src_node] = {}
        for neighbor in neighbor_list:
            self.table[neighbor.name()] = {}

        # initalize all values to inf for nodes
        for neighbor in neighbor_list + [source]:
            from_node = neighbor.name()
            self.table[from_node] = {}
            # for to_node in neighbor_list + [source]:
            #    self.table[from_node][to_node.name()] = [float('inf'), 'N/A']
            self.table[from_node][from_node] = [0, from_node]

        # set known neighbor values
        for neighbor in neighbor_list + [source]:
            self.table[self.src_node][neighbor.name()] = [neighbor.weight,
                                                          self.src_node]


    def update(self, packet):
        """ Uopdate neighboring node; makes adjacent edge adjustments """
        # see transmit_str() for format of packet
        n_name = packet['name']
        n_vector = packet['data']
        src_vector = self.table[self.src_node]
        self.table[n_name] = n_vector
        update = False


        # check if there's a new connection
        if (n_name not in src_vector and self.src_node in n_vector):
            src_vector[n_name] = [n_vector[self.src_node][0], self.src_node]
            update = True

        # update if direct link to neighbor is now cheaper
        n_route = n_vector[self.src_node]
        s_route = src_vector[n_name]
        if n_route[0] < s_route[0] and n_route[1] == self.src_node and n_name == s_route[1]:
            s_route = [n_route[0], self.src_node]
            update = True

        return update or self.__recompute()


    def remove_node(self, node_name):
        """ Remove all links directly from this node to node_name"""
        print self.table
        values = self.table[self.src_node][node_name]

        # first step in path to node
        for dest, (cost, first_step) in self.table[self.src_node].items():
            if first_step == node_name:
                del self.table[self.src_node][dest]

        # last step
        for src in self.table:
            for dest, cost_step in self.table[src].items():
                if cost_step == values:
                    del self.table[src][dest]


    def __recompute(self):
        """ Re-calculates everything, returns True if changes are made """
        changes = False
        # all nodes with a direct connection or connection from a neighbor
        destinations = set(
            [r for n in self.table.values() for r in n.keys()])

        # find the cheapest path to all these nodes
        for dest in destinations:
            cost = self.table[self.src_node].get(dest, [None, None])
            possible_costs = []
            # loop possible first steps
            for step1, (cost1, step0) in self.table[self.src_node].iteritems():
                if step1 == dest:
                    possible_costs.append([cost1, step0])
                # loop looking for second steps
                if step1 in self.table:
                    for n_dest, (cost2, step2) in self.table[step1].iteritems():
                        if n_dest == dest and n_dest != step2:
                            possible_costs.append([cost1 + cost2, step1])

            # assign the smallest one
            likely_min = min(possible_costs)
            # default to former path if cost unchanged
            if likely_min[0] != cost[0]:
                self.table[self.src_node][dest] = likely_min
                changes = True

        return changes


    def link_up(self, node_name, weight):
        """ Adds to routing table, returns True if changes are made """
        if node_name in self.table[self.src_node]:
            if self.table[self.src_node][node_name] == [weight, self.src_node]:
                return False

        self.table[self.src_node][node_name] = [weight, self.src_node]
        return True


    def linkup_str(self, dest_weight):
        """ Broadcast message for RT_UPDATE """
        return json.dumps({
            "type": RT_LINKUP,
            "name": self.src_node,
            "weight": dest_weight
        })


    def transmit_str(self, dest_weight):
        """ Broadcast message for RT_UPDATE """
        return json.dumps({
            "type": RT_UPDATE,
            "name": self.src_node,
            "weight": dest_weight,
            "ip": self.ip,
            "port": self.port,
            "data": self.table[self.src_node]
        })


    def __str__(self):
        rt = ""
        for client, (cost, first_step) in self.table[self.src_node].iteritems():
            rt += "Destination = {}, Cost = {}, Link = ({})\n".format(
                    client, cost, first_step)
        return rt
