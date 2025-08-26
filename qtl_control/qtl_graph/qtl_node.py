"""
Node for graph based tuneup

Nodes make up a directed graph with splits for decision making?

    N0
   /  \
  N1  F2
   \  /
    N3
Node does some action and returns a return_code which will decide what will happen next
"""
from enum import Enum


class ReturnCode(Enum):
    success = 0
    fail = 1
    fallback = 2

class GraphNode:
    def __init__(self, vertices=None, dependencies=None):
        self.vertices = vertices or dict()
        self.dependencies = dependencies or list()

        self.current_state = ReturnCode.fail

    def run(self) -> ReturnCode:
        node_result = self.node_execution()
        self.current_state = node_result

        return self.current_state

    def get_success_or_rerun(self):
        if self.current_state != ReturnCode.success:
            self.run_to()
        return self.current_state

    def node_execution():
        return ReturnCode.fail

    def add_vertex(self, returncode, node):
        existing_returns = self.vertices.get(returncode, [])
        existing_returns.append(node)
        self.vertices[returncode] = existing_returns
        node.dependencies.append(self)

    def run_to(self):
        """
        run everything up to current node
        """
        for dep in self.dependencies:
            dep.get_success_or_rerun()
        
        return self.run()
    
    def reset_return(self):
        self.current_state = ReturnCode.fail


class Graph:
    """
    Collection of nodes and helpers to combine them together
    """
    def __init__(self, graph_label):
        self.label = graph_label
        self.nodes = {}

    def add_node(self, node_label, new_node):
        self.nodes[node_label] = new_node

    def add_vertex_node(self, from_existing_node, return_code, new_node_label, new_node):
        self.nodes[new_node_label] = new_node
        self.nodes[from_existing_node].add_vertex(return_code, new_node)

    def run_to_node(self, node_label):
        self.nodes[node_label].run_to()