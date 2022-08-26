from copy import copy
from typing import List, Optional, TypeVar

from faas.system import FunctionDeployment
from faas.util.rwlock import ReadWriteLock
from .api import FunctionDeploymentService

I = TypeVar('I', bound=FunctionDeployment)


class InMemoryDeploymentService(FunctionDeploymentService[I]):

    def __init__(self, deployments: List[I]):
        self.deployments = deployments
        self._deployments = {}
        self.rw_lock = ReadWriteLock()
        for deployment in deployments:
            self._deployments[deployment.name] = deployment

    def get_deployments(self) -> List[I]:
        with self.rw_lock.lock.gen_rlock():
            return copy(self.deployments)

    def get_by_name(self, fn_name: str) -> Optional[I]:
        with self.rw_lock.lock.gen_rlock():
            return self._deployments.get(fn_name)

    def exists(self, fn_name: str) -> bool:
        with self.rw_lock.lock.gen_rlock():
            return self._exists(fn_name)

    def _exists(self, fn_name: str) -> bool:
        return self._deployments.get(fn_name, None) is not None

    def remove(self, function_name: str):
        with self.rw_lock.lock.gen_wlock():
            if self._exists(function_name):
                self.deployments = [x for x in self.deployments if x.name != function_name]
                del self._deployments[function_name]

    def add(self, deployment: I):
        with self.rw_lock.lock.gen_wlock():
            if not self._exists(deployment.name):
                self.deployments.append(deployment)
                self._deployments[deployment.name] = deployment
