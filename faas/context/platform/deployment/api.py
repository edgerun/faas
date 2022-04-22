import abc
from typing import List, Optional, TypeVar, Generic

from faas.system import FunctionDeployment

I = TypeVar('I', bound=FunctionDeployment)


class FunctionDeploymentService(abc.ABC, Generic[I]):

    def get_by_name(self, fn_name) -> Optional[I]:
        """
        Tries to find a FunctionDeployment which represents a Function with the given name
        :param fn_name: the function name to look for
        :return: None if no FunctionDeployment exists, otherwise a FunctionDeployment
        """
        ...

    def get_deployments(self) -> List[I]:
        """
        Returns all deployed and suspended FunctionDeployments
        :return: a list of FunctionDeployments
        """
        ...

    def exists(self, name: str) -> bool:
        """
        Checks whether a FunctionDeployment with the given name exists
        :param name: name of the FunctionDeployment
        :return: true if already deployed, false otherwise
        """
        ...

    def add(self, deployment: I):
        ...

    def remove(self, function_name: str): ...
