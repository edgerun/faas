import logging
from typing import Dict, List, Optional, TypeVar, Callable, Union

from faas.util.constant import function_replica_delete, function_replica_add, function_replica_scale_up, \
    function_replica_scale_down, function_replica_state_change, function_replica_shutdown
from faas.util.rwlock import ReadWriteLock
from ...observer.api import Observer

logger = logging.getLogger(__name__)

from faas.system import FunctionReplicaState, FunctionReplica, FunctionDeployment
from faas.context.platform.node.api import NodeService
from faas.context.platform.deployment.api import FunctionDeploymentService
from .api import FunctionReplicaService, FunctionReplicaFactory

I = TypeVar('I', bound=FunctionReplica)
D = TypeVar('D', bound=FunctionDeployment)


class InMemoryFunctionReplicaService(FunctionReplicaService[I]):
    """
    A thread-safe static implementation of the FunctionReplicaService interface that stores all replicas in memory.
    """

    def __init__(self, node_service: NodeService, deployment_service: FunctionDeploymentService[D],
                 replica_factory: FunctionReplicaFactory[D, I]):
        super().__init__()
        self.node_service = node_service
        self.deployment_service = deployment_service
        self.replica_factory = replica_factory
        self._replicas: Dict[str, I] = {}
        self.rw_lock = ReadWriteLock()
        self.observers: List[Observer] = []

    def get_function_replicas(self) -> List[I]:
        with self.rw_lock.lock.gen_rlock():
            replicas = list(self._replicas.values())
            return replicas

    def find_by_predicate(self, predicate: Callable[[I], bool], running: bool = True,
                          state: FunctionReplicaState = None) -> \
            List[I]:
        found = None
        with self.rw_lock.lock.gen_rlock():
            replicas = self.get_function_replicas()
            for replica in replicas:
                if running and replica.state != FunctionReplicaState.RUNNING:
                    continue
                if state is not None and replica.state != state:
                    continue
                if predicate(replica):
                    found = replica
                    break
            return found

    def get_function_replicas_of_deployment(self, fn_deployment_name, running: bool = True,
                                            state: FunctionReplicaState = None) -> List[
        I]:
        with self.rw_lock.lock.gen_rlock():
            logger.debug(f'get_function_replicas_of_deployment for {fn_deployment_name}')
            containers = []
            for replica in self._replicas.values():
                if running and replica.state != FunctionReplicaState.RUNNING:
                    continue
                if state is not None and replica.state != state:
                    continue
                if fn_deployment_name == replica.fn_name:
                    containers.append(replica)
            logger.debug(f'found {len(containers)} containers for {fn_deployment_name}')
            return containers

    def find_function_replicas_with_labels(self, labels: Dict[str, str] = None, node_labels=None, running: bool = True,
                                           state: str = None) -> List[
        I]:
        if node_labels is None:
            node_labels = dict()
        logger.debug(f"find containers with labels: {labels}, and node labels: {node_labels}")
        pods = []
        with self.rw_lock.lock.gen_rlock():
            for replica in self._replicas.values():
                if running and replica.state != FunctionReplicaState.RUNNING:
                    continue
                if state is not None and replica.state != state:
                    continue
                matches = True
                if labels is not None:
                    pod_labels = replica.labels
                    matches = self.matches_labels(labels, pod_labels)
                node = self.node_service.find(replica.node.name)
                if not matches or node is None:
                    continue
                if node_labels is not None:
                    matches = matches and self.matches_labels(node_labels, node.labels)
                if matches:
                    pods.append(replica)
            return pods

    def get_function_replica_by_id(self, replica_id: str) -> Optional[I]:
        with self.rw_lock.lock.gen_rlock():
            replicas = list(filter(lambda r: r.replica_id == replica_id, self._replicas.values()))
            replica = None
            if len(replicas) == 1:
                replica = replicas[0]
            return replica

    def get_function_replica_with_id(self, replica_id: str) -> Optional[I]:
        logger.debug(f'find replica with id: {replica_id}')
        with self.rw_lock.lock.gen_rlock():
            found = None
            for replica in self._replicas.values():
                if replica.replica_id == replica_id:
                    found = replica
                    break
            return found

    def get_function_replicas_on_node(self, node_name: str) -> List[I]:
        logger.debug(f'find containers on ode {node_name}')
        with self.rw_lock.lock.gen_rlock():
            replicas = list(filter(lambda r: r.node.name == node_name, self._replicas.values()))
            return replicas

    def shutdown_function_replica(self, replica_id: str):
        logger.info(f"Shutdown replica with ID: {replica_id}")
        with self.rw_lock.lock.gen_wlock():
            self._shutdown_function_replica(replica_id)
        replica = self._replicas[replica_id]
        for observer in self.observers:
            payload = {
                'request': replica,
                'response': replica
            }
            observer.fire(function_replica_shutdown, payload)

    def _shutdown_function_replica(self, replica_id: str):
        try:
            self._replicas[replica_id].state = FunctionReplicaState.SHUTDOWN
        except KeyError:
            logger.info(f'Wanted to shutdown non existing replica with ID "{replica_id}"')

    def delete_function_replica(self, replica_id: str):
        logger.info(f"Shutdown replica with ID: {replica_id}")
        with self.rw_lock.lock.gen_wlock():
            self._delete_function_replica(replica_id)
            replica = self._replicas[replica_id]
        for observer in self.observers:
            payload = {
                'request': replica,
                'response': replica
            }
            observer.fire(function_replica_delete, payload)

    def _delete_function_replica(self, replica_id: str):
        try:
            self._replicas[replica_id].state = FunctionReplicaState.DELETE
        except KeyError:
            logger.info(f'Wanted to delete non existing replica with ID "{replica_id}"')

    def add_function_replica(self, replica: I):
        logger.info(f"Add replica with ID: {replica.replica_id}")
        with self.rw_lock.lock.gen_wlock():
            self._add_function_replica(replica)
        for observer in self.observers:
            payload = {
                'request': replica,
                'response': replica,
            }
            observer.fire(function_replica_add, payload)

    def _add_function_replica(self, replica: I) -> I:
        stored_replica = self._replicas.get(replica.replica_id, None)
        if stored_replica is not None:
            if stored_replica.state == FunctionReplicaState.PENDING or stored_replica.state == FunctionReplicaState.RUNNING:
                # only update pod in case it is pending or running, prevents from updating a not running to running pod
                logger.info(f"Update replica: {replica}")
                self._replicas[replica.replica_id] = replica
        else:
            logger.info(f"Create replica: {replica}")
            self._replicas[replica.replica_id] = replica
        return replica

    def matches_labels(self, labels, to_match):
        for label in labels:
            to_match_value = to_match.get(label, None)
            if to_match_value is None or to_match_value != labels[label]:
                return False
        return True

    def scale_down(self, function_name: str, remove: Union[int, List[I]]) -> List[I]:
        with self.rw_lock.lock.gen_wlock():
            if self.deployment_service.get_by_name(function_name) is None:
                raise ValueError(f'FunctionDeployment {function_name} does not exist.')
            if type(remove) is int:
                replicas = self._replicas[function_name]
                all_replicas = len(replicas)
                # just choose the last ones that were added
                removed_replicas: List[I] = replicas[all_replicas - remove:]
                for removed in removed_replicas:
                    self._delete_function_replica(removed.replica_id)
                payload = {
                    'request': remove,
                    'response': removed_replicas
                }
                for observer in self.observers:
                    observer.fire(function_replica_scale_down, payload)
                return removed_replicas
            elif type(remove) is list:
                for replica in remove:
                    self._delete_function_replica(replica.replica_id)
                payload = {
                    'request': remove,
                    'response': remove
                }
                for observer in self.observers:
                    observer.fire(function_replica_scale_down, payload)
                return remove
            else:
                raise ValueError(f'Unknown type {type(remove)} for remove argument')

    def scale_up(self, function_name: str, add: Union[int, List[I]]) -> List[I]:
        with self.rw_lock.lock.gen_wlock():
            if self.deployment_service.get_by_name(function_name) is None:
                raise ValueError(f'FunctionDeployment {function_name} does not exist.')
            if type(add) is int:
                replicas = []
                fn = self.deployment_service.get_by_name(function_name)
                for i in range(add):
                    container = fn.deployment_ranking.get_first()
                    replica = self.replica_factory.create_replica(container.labels, container, fn)
                    replicas.append(replica)
                    self._add_function_replica(replica)
                payload = {
                    'request': add,
                    'response': replicas
                }
                for observer in self.observers:
                    observer.fire(function_replica_scale_up, payload)
                return replicas
            elif type(add) is List[I]:
                for replica in add:
                    self._add_function_replica(replica)
                payload = {
                    'request': add,
                    'response': add
                }
                for observer in self.observers:
                    observer.fire(function_replica_scale_up, payload)
                return add
            else:
                raise ValueError(f'Unknown type {type(add)} for add argument')

    def register(self, observer: Observer):
        self.observers.append(observer)
        for replica in self.get_function_replicas():
            observer.fire(function_replica_add, {'request': replica, 'response': replica})

    def set_state(self, replica: FunctionReplica, state: FunctionReplicaState):
        old_state = replica.state
        with self.rw_lock.lock.gen_wlock():
            replica.state = state
        payload = {
            'replica': replica,
            'old': old_state,
            'new': state
        }
        for observer in self.observers:
            observer.fire(function_replica_state_change, payload)
