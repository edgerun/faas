from copy import copy
from typing import List, Optional, Dict, TypeVar

from faas.context.platform.node.api import NodeService
from faas.system.core import NodeState, FunctionNode
from faas.util.rwlock import ReadWriteLock

I = TypeVar('I', bound=FunctionNode)


class InMemoryNodeService(NodeService[I]):

    def __init__(self, zones: List[str], nodes: List[I]):
        self.zones = zones
        self.nodes = nodes
        self._nodes_by_name = {}
        for node in self.nodes:
            self._nodes_by_name[node.name] = node
        self.rwlock = ReadWriteLock()

    def get_zones(self) -> List[str]:
        return copy(self.zones)

    def get_nodes(self) -> List[I]:
        with self.rwlock.lock.gen_rlock():
            return copy(self.nodes)

    def get_nodes_by_name(self) -> Dict[str, I]:
        with self.rwlock.lock.gen_rlock():
            return copy(self._nodes_by_name)

    def find(self, node_name: str) -> Optional[I]:
        with self.rwlock.lock.gen_rlock():
            for node in self.nodes:
                if node.name == node_name:
                    return node
        return None

    def find_nodes_in_zone(self, zone: str) -> List[I]:
        with self.rwlock.lock.gen_rlock():
            collected = []
            for node in self.nodes:
                if node.cluster == zone:
                    collected.append(node)
            return collected

    def add_node(self, node: FunctionNode):
        with self.rwlock.lock.gen_wlock():
            self.nodes.append(node)
            self._nodes_by_name[node.name] = node

    def remove_nod(self, node: str):
        with self.rwlock.lock.gen_wlock():
            del self._nodes_by_name[node]
            self.nodes = filter(lambda n: n.name != node, self.nodes)

    def set_state(self, node: str, state: NodeState):
        with self.rwlock.lock.gen_wlock():
            self._nodes_by_name[node].state = state
