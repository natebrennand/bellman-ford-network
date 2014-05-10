
import routing_table
import node
import unittest


def make_node_10():
    src_node = node.Node('123', 10, 0)
    neighbors = [
        node.Node('123', 11, 1),
        node.Node('123', 12, 2),
        node.Node('123', 13, 5),
    ]
    src_routing_table = routing_table.RoutingTable(neighbors, src_node)
    return src_node, src_routing_table

def make_node_11():
    node11 = node.Node('123', 11, 0)
    neighbors_11 = [
        node.Node('123', 10, 1),
        node.Node('123', 13, 5),
        node.Node('123', 15, 1),
    ]
    node11_routing_table = routing_table.RoutingTable(neighbors_11, node11)
    return node11, node11_routing_table

def make_node_15():
    node15 = node.Node('123', 15, 0)
    neighbors_15 = [
        node.Node('123', 11, 2),
        node.Node('123', 16, 1),
    ]
    node15_routing_table = routing_table.RoutingTable(neighbors_15, node15)
    return node15, node15_routing_table

def make_node_16():
    node16 = node.Node('123', 16, 0)
    neighbors_16 = [
        node.Node('123', 15, 1),
        node.Node('123', 13, 1),
    ]
    node16_routing_table = routing_table.RoutingTable(neighbors_16, node16)
    return node16, node16_routing_table


class TestRoutingTable(unittest.TestCase):

    def __update(self, a, b, rt):
        return a.update({
            'name': b.name(),
            'data': rt.table[b.name()],
        })

    def Test_Basic_Update(self):
        a, a_rt = make_node_10()
        b, b_rt = make_node_11()

        # adds node 16 to network
        self.assertTrue(self.__update(a_rt, b, b_rt))

    def Test_Redundant_Update(self):
        a, a_rt = make_node_10()
        b, b_rt = make_node_11()

        # adds node 11 to network
        self.assertTrue(self.__update(a_rt, b, b_rt))
        # should add nothing
        self.assertFalse(self.__update(a_rt, b, b_rt))
        # should add nothing
        self.assertFalse(self.__update(a_rt, b, b_rt))

    def Test_Update_Propogation(self):
        a, a_rt = make_node_10()
        b, b_rt = make_node_11()
        c, c_rt = make_node_15()
        d, d_rt = make_node_16()

        # update 10 with 11
        self.assertTrue(self.__update(a_rt, b, b_rt))
        # update 11 with 15
        self.assertTrue(self.__update(b_rt, c, c_rt))
        # update 15 with 16
        self.assertTrue(self.__update(c_rt, d, d_rt))
        # update 11 with an updated 15
        self.assertTrue(self.__update(b_rt, c, c_rt))
        # update 10 with an update 11
        self.assertTrue(self.__update(a_rt, b, b_rt))

