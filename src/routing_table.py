
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
        self.own_edges = dict()

        # add own edges
        self.own_edges = dict((n.name(), [n.weight, self.src_node]) for n in neighbor_list)

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
        p_name = packet['name']
        self.table[p_name] = packet['data']
        src_vector = self.table[self.src_node]
        p_vector = self.table[p_name]
        update = False

        # check if there's a new connection to this node
        if p_name not in src_vector and self.src_node in p_vector:
            print 'New connection to {}'.format(p_name)
            # add edge to this node's vector
            src_vector[p_name] = [p_vector[self.src_node][0], self.src_node]
            self.own_edges[p_name] = [p_vector[self.src_node][0], self.src_node]
            update = True

        # check if a cheaper connection exists
        elif self.src_node in p_vector:
            other_cost = p_vector[self.src_node]
            our_cost = src_vector[p_name]
            if (other_cost[0] < our_cost[0] and  # cheaper
                    other_cost[1] == p_name):  # direct
                src_vector[p_name] = [other_cost[0], self.src_node]
                update = True

        return update or self.__recompute()


    def remove_node(self, node_name):
        """ Remove all links directly from this node to node_name"""
        # in set of own edges
        if node_name in self.own_edges:
            del self.own_edges[node_name]

        # if has a set of edges
        if node_name in self.table:
            del self.table[node_name]

        # first step in path to node
        for dest, (cost, first_step) in self.table[self.src_node].items():
            if first_step == node_name:
                del self.table[self.src_node][dest]

        # last step
        if node_name in self.table[self.src_node]:
            values = self.table[self.src_node][node_name]
            for src in self.table:
                for dest, cost_step in self.table[src].items():
                    if cost_step == values:
                        del self.table[src][dest]


    def __recompute(self):
        """ Re-calculates everything, returns True if changes are made """
        changes = False
        # all nodes with a direct connection or connection from a neighbor
        destinations = set(
            [r for n in self.table.values() for r in n.keys() if r != self.src_node] +
            self.own_edges.keys())

        # find the cheapest path to all these nodes
        for goal_dest in destinations:
            cost = self.table[self.src_node].get(goal_dest, [None, None])
            possible_costs = []
            # loop possible first steps
            # start with step0, eventually to mid_dest, then step1
            for mid_dest, (cost1, step0) in self.table[self.src_node].items() + self.own_edges.items():
                if mid_dest == goal_dest:
                    possible_costs.append([cost1, step0])
                # loop looking for second steps
                if mid_dest in self.table:
                    for dest, (cost2, step1) in self.table[mid_dest].iteritems():
                        # if right destination & doesn't end with 0 steps
                        if dest == goal_dest and dest != step1:
                            if self.src_node != step1: # prevent looping
                                possible_costs.append([cost1 + cost2, mid_dest])

            # skip if no options
            if not possible_costs:  
                continue
            # assign the smallest one
            likely_min = min(possible_costs)
            # ignore if cost unchanged
            if likely_min[0] != cost[0]:
                self.table[self.src_node][goal_dest] = likely_min
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
