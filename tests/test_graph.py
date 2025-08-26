from qtl_control.qtl_graph.qtl_node import GraphNode, ReturnCode, Graph

class TestNode(GraphNode):
    ORDER_OF_NODES = []
    def __init__(self, id):
        super().__init__()
        self.id = id

    def node_execution(self):
        self.ORDER_OF_NODES.append(self.id)
        return ReturnCode.success

def test_graphnode():
    TestNode.ORDER_OF_NODES = []
    n0 = TestNode(0)
    n1 = TestNode(1)
    n0.add_vertex(ReturnCode.success, n1)
    assert n0 in n1.dependencies
    
    n1.run_to()
    assert TestNode.ORDER_OF_NODES == [0, 1]

def test_double_dependency():
    TestNode.ORDER_OF_NODES = []
    n0 = TestNode(0)
    n1 = TestNode(1)
    n2 = TestNode(2)

    n0.add_vertex(ReturnCode.success, n2)
    n1.add_vertex(ReturnCode.success, n2)
    
    n2.run_to()
    assert TestNode.ORDER_OF_NODES == [0, 1, 2]

def test_large_tree():
    n0 = TestNode(0)
    n1 = TestNode(1)
    n2 = TestNode(2)
    n3 = TestNode(3)
    n4 = TestNode(4)
    n5 = TestNode(5)
    n6 = TestNode(6)

    n0.add_vertex(ReturnCode.success, n1)    
    n2.add_vertex(ReturnCode.success, n1)
    n2.add_vertex(ReturnCode.success, n3)
    n4.add_vertex(ReturnCode.success, n3)
    n1.add_vertex(ReturnCode.success, n5)
    n1.add_vertex(ReturnCode.success, n6)
    n3.add_vertex(ReturnCode.success, n6)

    TestNode.ORDER_OF_NODES = []
    n6.run_to()
    assert TestNode.ORDER_OF_NODES == [0, 2, 1, 4, 3, 6]

    TestNode.ORDER_OF_NODES = []
    n5.run_to()
    assert TestNode.ORDER_OF_NODES == [5]

def test_graph():
    graph = Graph("test")
    
    n0 = TestNode(0)
    n1 = TestNode(1)
    graph.add_node("node0", n0)
    graph.add_vertex_node("node0", ReturnCode.success, "node1", n1)

    TestNode.ORDER_OF_NODES = []
    graph.run_to_node("node1")
    assert TestNode.ORDER_OF_NODES == [0, 1]
