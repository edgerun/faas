from typing import List, Any

from faas.context import PlatformContext
from faas.context.observer.api import Observer
from faas.system import FunctionDeployment, FunctionReplica, FunctionReplicaState
from faas.util.constant import function_label, api_gateway_type_label, zone_label, function_replica_add, \
    function_replica_scale_up, function_replica_scale_down, function_replica_state_change, \
    function_replica_shutdown


class LoadBalancerOptimizer:
    def update(self): ...

    def get_running_replicas(self, function: str) -> List[FunctionReplica]: ...

    def get_functions(self) -> List[FunctionDeployment]: ...

    def add_replica(self, replica: FunctionReplica): ...

    def remove_replica(self, replica: FunctionReplica): ...

    def add_replicas(self, replicas: List[FunctionReplica]): ...

    def remove_replicas(self, replicas: List[FunctionReplica]): ...


class GlobalLoadBalancerOptimizer(LoadBalancerOptimizer):

    def __init__(self, context: PlatformContext):
        self.context = context
        self.observer = LoadBalancerObserver(self)
        context.replica_service.register(self.observer)

    def get_running_replicas(self, function: str) -> List[FunctionReplica]:
        replica_service = self.context.replica_service
        return replica_service.get_function_replicas_of_deployment(function, running=True)

    def get_functions(self) -> List[FunctionDeployment]:
        deployment_service = self.context.deployment_service
        functions = [d for d in deployment_service.get_deployments() if
                     d.labels.get(function_label) and d.labels.get(function_label) != api_gateway_type_label]
        return functions


class LoadBalancerObserver(Observer):

    def __init__(self, lb: LoadBalancerOptimizer):
        self.lb = lb

    def fire(self, event: str, value: Any):
        if event == function_replica_add:
            replica: FunctionReplica = value['response']
            if replica.state == FunctionReplicaState.RUNNING:
                self.lb.add_replica(replica)
        if event == function_replica_shutdown:
            replica = value['response']
            self.lb.remove_replica(replica)
        if event == function_replica_scale_up:
            replicas: List[FunctionReplica] = value['response']
            replicas = [r for r in replicas  if r.state == FunctionReplicaState.RUNNING]
            self.lb.add_replicas(replicas)
        if event == function_replica_scale_down:
            replicas = value['response']
            self.lb.remove_replicas(replicas)
        if event == function_replica_state_change:
            state = value['new']
            if state == FunctionReplicaState.RUNNING:
                self.lb.add_replica(value['replica'])

class LocalizedLoadBalancerOptimizer(LoadBalancerOptimizer):

    def __init__(self, context: PlatformContext, cluster: str):
        self.context = context
        self.cluster = cluster
        self.observer = LoadBalancerObserver(self)

    def get_functions(self) -> List[FunctionDeployment]:
        deployment_service = self.context.deployment_service
        functions = [d for d in deployment_service.get_deployments() if
                     d.labels.get(function_label) and d.labels.get(function_label) != api_gateway_type_label]
        return functions

    def get_running_replicas(self, function: str) -> List[FunctionReplica]:
        replicas = self.context.replica_service.find_function_replicas_with_labels(labels={
            function_label: function}, node_labels={zone_label: self.cluster}, running=True)

        all_load_balancers = self.context.replica_service.find_function_replicas_with_labels(labels={
            function_label: api_gateway_type_label
        })
        other_load_balancers = [l for l in all_load_balancers if l.labels[zone_label] != self.cluster]
        for lb in other_load_balancers:
            other_cluster = lb.labels[zone_label]
            other_replicas = self.context.replica_service.find_function_replicas_with_labels(labels={
                function_label: function,
            }, node_labels={zone_label: other_cluster}, running=True)
            if len(other_replicas) > 0:
                replicas.append(lb)
        return replicas
