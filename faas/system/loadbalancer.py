from typing import List

from faas.context import PlatformContext
from faas.system import FunctionDeployment, FunctionReplica
from faas.util.constant import function_label, api_gateway_type_label, zone_label


class LoadBalancer:

    def update(self): ...

    def get_running_replicas(self, function: str) -> List[FunctionReplica]: ...

    def get_functions(self) -> List[FunctionDeployment]: ...

    def add_replica(self, replica: FunctionReplica): ...

    def remove_replica(self, replica: FunctionReplica): ...

class GlobalLoadBalancer(LoadBalancer):

    def __init__(self, context: PlatformContext):
        self.context = context

    def get_running_replicas(self, function: str) -> List[FunctionReplica]:
        replica_service = self.context.replica_service
        return replica_service.get_function_replicas_of_deployment(function, running=True)

    def get_functions(self) -> List[FunctionDeployment]:
        deployment_service = self.context.deployment_service
        functions = [d for d in deployment_service.get_deployments() if
                     d.labels.get(function_label) and d.labels.get(function_label) != api_gateway_type_label]
        return functions


class LocalizedLoadBalancer(LoadBalancer):

    def __init__(self, context: PlatformContext, cluster: str):
        self.context = context
        self.cluster = cluster

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
