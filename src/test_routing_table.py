
import routing_table
import node
import unittest


def make_node_10():
    src_node = node.Node('123', 10, 0)
    neighbors = [
        node.Node('123', 11, 1),
        node.Node('123', 13, 5),
    ]
    src_routing_table = routing_table.RoutingTable(neighbors, src_node)
    return src_node, src_routing_table

def make_node_11():
    node11 = node.Node('123', 11, 0)
    neighbors_11 = [
        node.Node('123', 10, 1),
        node.Node('123', 13, 7),
        node.Node('123', 15, 1),
    ]
    node11_routing_table = routing_table.RoutingTable(neighbors_11, node11)
    return node11, node11_routing_table

def make_node_13():
    node13 = node.Node('123', 13, 0)
    neighbors_13 = [
        node.Node('123', 10, 5),
        node.Node('123', 11, 7),
    ]
    node13_routing_table = routing_table.RoutingTable(neighbors_13, node13)
    return node13, node13_routing_table

def make_node_15():
    node15 = node.Node('123', 15, 0)
    neighbors_15 = [
        node.Node('123', 11, 1),
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

    def __has_route(self, rt, n):
        return n in rt.table[rt.src_node]

    def test_Basic_Update(self):
        a, a_rt = make_node_10()
        b, b_rt = make_node_11()

        # adds node 16 to network
        self.assertTrue(self.__update(a_rt, b, b_rt))

    def test_Redundant_Update(self):
        a, a_rt = make_node_10()
        b, b_rt = make_node_11()

        # adds node 11 to network
        self.assertTrue(self.__update(a_rt, b, b_rt))
        # should add nothing
        self.assertFalse(self.__update(a_rt, b, b_rt))
        # should add nothing
        self.assertFalse(self.__update(a_rt, b, b_rt))

    def test_Update_Propogation(self):
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

    def test_remove_node(self):
        a, a_rt = make_node_10()
        b, b_rt = make_node_11()
        c, c_rt = make_node_15()
        self.assertTrue(self.__update(a_rt, b, b_rt))
        self.assertTrue(self.__update(b_rt, a, a_rt))
        self.assertTrue(self.__update(b_rt, c, c_rt))
        self.assertTrue(self.__update(c_rt, b, b_rt))
        self.assertTrue(self.__update(a_rt, b, b_rt))

        b_rt.remove_node(c.name())
        self.assertFalse(self.__has_route(b_rt, c.name()))

        self.assertTrue(self.__update(a_rt, b, b_rt))
        self.__update(a_rt, b, b_rt)

        temp, temp_rt = make_node_10()
        temp_rt.table[b.name()][temp.name()] = [1, b.name()]
        temp_rt.table[b.name()]['123:13'] = [6, temp.name()] # routed through 10

        self.assertDictEqual(a_rt.table, temp_rt.table)

    def test_remove_link(self):
        a, a_rt = make_node_10()
        b, b_rt = make_node_11()
        c, c_rt = make_node_13()

        self.__update(a_rt, b, b_rt)
        self.__update(b_rt, a, a_rt)

        self.__update(b_rt, c, c_rt)
        self.__update(c_rt, b, b_rt)

        self.__update(a_rt, c, c_rt)
        self.__update(c_rt, a, a_rt)

        # delete link between 

        #self.assertFalse(True)

