import abc
from typing import Tuple, Optional

from faas.system import FunctionReplica


class GlobalScheduler(abc.ABC):

    def find_cluster(self, replica: FunctionReplica) -> Tuple[str, str]: ...


class LocalScheduler(abc.ABC):

    def schedule(self, replica: FunctionReplica) -> Optional[str]: ...
