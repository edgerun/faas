import abc
from typing import List, Optional, Dict, Callable, Generic, TypeVar, Union

from ...observer.api import Observer
from ....system.core import FunctionReplica, FunctionReplicaState, FunctionContainer, FunctionDeployment

I = TypeVar('I', bound=FunctionReplica)
D = TypeVar('D', bound=FunctionDeployment)


class FunctionReplicaService(abc.ABC, Generic[I]):

    def find_by_predicate(self, predicate: Callable[[I], bool], running: bool = True,
                          state: FunctionReplicaState = None) -> \
            List[I]:
        ...

    def get_function_replicas(self) -> List[I]:
        raise NotImplementedError()

    def get_function_replicas_of_deployment(self, deployment_name, running: bool = True,
                                            state: FunctionReplicaState = None) -> \
            List[I]:
        """
        param name: original name of the deployment
        """
        raise NotImplementedError()

    def find_function_replicas_with_labels(self, labels: Dict[str, str] = None, node_labels=None,
                                           running: bool = True, state: FunctionReplicaState = None) -> List[
        I]:
        raise NotImplementedError()

    def get_function_replica_by_id(self, replica_id: str) -> Optional[I]:
        raise NotImplementedError()

    def get_function_replicas_on_node(self, node_name: str) -> List[I]:
        raise NotImplementedError()

    def shutdown_function_replica(self, replica_id: str):
        raise NotImplementedError()

    def add_function_replica(self, functionReplica: I) -> I:
        raise NotImplementedError()

    def delete_function_replica(self, replica_id: str): ...

    def scale_down(self, function_name: str, remove: Union[int, List[I]]) -> List[I]: ...

    def scale_up(self, function_name: str, add: Union[int, List[I]]) -> List[I]: ...

    def register(self, observer: Observer): ...

    def set_state(self, replica: FunctionReplica, state: FunctionReplicaState): ...


class FunctionReplicaFactory(abc.ABC, Generic[D, I]):

    def create_replica(self, labels: Dict[str, str], fn_container: FunctionContainer,
                       fn_deployment: D) -> I: ...
