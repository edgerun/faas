import abc
import enum
from dataclasses import dataclass
from typing import List, Dict, Union, Any
from typing import Optional


class WorkloadConfiguration(abc.ABC):
    pass


def counter(start: int = 1):
    n = start
    while True:
        yield n
        n += 1


@dataclass
class ScalingConfiguration:
    scale_min: int = 1
    scale_max: int = 20
    # determines the percentage how many pods
    scale_factor: int = 1
    scale_zero: bool = False


class NodeState(enum.Enum):
    READY = 1
    NOT_READY = 2


class ScheduleEvent(enum.Enum):
    QUEUE = 1
    START = 2
    FINISH = 3


class FunctionReplicaState(enum.Enum):
    CONCEIVED = 1
    PENDING = 2
    RUNNING = 3
    SHUTDOWN = 4
    DELETE = 5


@dataclass
class FunctionImage:
    # the manifest list (docker image) name
    image: str

    def __init__(self, image: str):
        self.image = image


class ResourceConfiguration():

    def __init__(self, requirements: Dict[str, Any], limits: Dict[str, Any] = None):
        self.requirements = requirements
        self.limits = limits

    def get_resource_requirements(self) -> Dict:
        """
        Defines the resource requirements that a node must meet in order to eligible for scheduling.
        Has to be always defined and a default value must be provided.
        :return: resource requirements for scheduling
        """
        return self.requirements

    def get_resource_limits(self) -> Optional[Dict]:
        """
        Returns the upper limit of resource usage. Is optional and therefore can be None
        :return: an optional dict that contains upper limits for resource usage
        """
        return self.limits

    def __str__(self):
        return str(self.get_resource_requirements())

    def __repr__(self):
        return str(self.get_resource_requirements())


@dataclass
class Function:
    name: str
    fn_images: List[FunctionImage]
    labels: Dict[str, str]

    def __init__(self, name: str, fn_images: List[FunctionImage], labels: Dict[str, str] = None):
        self.fn_images = fn_images
        self.name = name
        self.labels = labels if labels is not None else {}

    def get_image(self, image: str) -> Optional[FunctionImage]:
        for fn_image in self.fn_images:
            if fn_image.image == image:
                return fn_image
        return None


@dataclass
class FunctionContainer:
    fn_image: FunctionImage
    resource_config: ResourceConfiguration
    labels: Dict[str, str]

    def __init__(self, fn_image: FunctionImage, resource_config: ResourceConfiguration,
                 labels: Dict[str, str] = None):
        self.fn_image = fn_image
        self.resource_config = resource_config
        self.labels = labels if labels is not None else {}

    @property
    def image(self):
        return self.fn_image.image

    def get_resource_requirements(self):
        return self.resource_config.get_resource_requirements()


class FunctionNode:
    name: str
    arch: str
    cpus: int
    ram: int
    netspeed: int
    labels: Dict[str, str]
    allocatable: Dict[str, str]
    cluster: Optional[str]
    state: NodeState

    def __init__(self, name: str, arch: str, cpus: int, ram: int, netspeed: int, labels: Dict[str, str],
                 allocatable: Dict[str, str], cluster: Optional[str], state: NodeState):
        self.name = name
        self.arch = arch
        self.cpus = cpus
        self.ram = ram
        self.netspeed = netspeed
        self.labels: Dict[str, str] = labels
        self.allocatable = allocatable
        self.cluster = cluster
        self.state = state


@dataclass
class DeploymentRanking:
    """
    The DeploymentRanking is used to determine at any time which DeploymentRanking to deploy for the associated
    FunctionDeployment.
    Users can modify this ranking during runtime to dynamically choose a concrete implementation (FunctionContainer)
    for a Function (FunctionDeployment).
    """
    containers: List[FunctionContainer]
    function_factor: Dict[str, float]

    def __init__(self, containers: List[FunctionContainer], function_factor: Dict[str, float] = None):
        self.containers = containers.copy()
        self.function_factor = function_factor
        if self.function_factor is None:
            self.function_factor = {}
            for container in self.containers:
                self.function_factor[container.image] = 1

    def set_first(self, container: FunctionContainer):
        """
        Sets the given container into the first position and pushes all other containers back by one.
        """
        index = self._find_index(container)
        if index is None:
            raise ValueError(f'Container {container.image} not found in ranking.')

        updated = self.containers[:index] + self.containers[index + 1:]
        self.containers = [container] + updated

    def _find_index(self, container: FunctionContainer) -> Optional[int]:
        try:
            return self.containers.index(container)
        except ValueError:
            return None

    def get_first(self):
        return self.containers[0]


@dataclass
class FunctionDeployment:
    fn: Function
    fn_containers: List[FunctionContainer]
    scaling_configuration: ScalingConfiguration
    deployment_ranking: DeploymentRanking

    def get_services(self):
        return list(map(lambda fn_container: fn_container.fn_image, self.fn_containers))

    def get_containers(self):
        return self.fn_containers

    def get_container(self, image: str) -> Optional[FunctionContainer]:
        for fn_image in self.fn_containers:
            if fn_image.image == image:
                return fn_image
        return None

    @property
    def name(self):
        return self.fn.name

    @property
    def labels(self):
        return self.fn.labels.copy()


class FunctionReplica:
    """
    A function replica is an instance of a function running on a specific node.
    """
    # name must be unique to this specific replica, i.e., UUID
    replica_id: str
    _labels: Dict[str, str]
    function: FunctionDeployment
    container: FunctionContainer
    node: Optional[FunctionNode]
    state: FunctionReplicaState

    def __init__(self, replica_id: str, labels: Dict[str, str], function: FunctionDeployment,
                 container: FunctionContainer, node: Optional[FunctionNode], state: FunctionReplicaState):
        self.replica_id = replica_id
        self._labels = labels
        self.function = function
        self.container = container
        self.node = node
        self.state = state

    @property
    def fn_name(self):
        return self.function.name

    @property
    def image(self):
        return self.container.image

    @property
    def labels(self):
        # own labels have highest priority (i.e., _labels will overwrite (function.labels | container.labels)
        labels = self.function.labels.copy()
        labels.update(self.container.labels)
        labels.update(self._labels)
        return labels


# TODO add functionrequest to trace when started

@dataclass
class FunctionRequest:
    request_id: int
    client: str
    name: str
    body: str
    start: float
    # in bytes
    size: int = None
    replica: FunctionReplica = None
    headers: Dict = None

    id_generator = counter()

    def __init__(self, name, start: float, size=None, request_id=None, body=None, client=None, replica=None,
                 headers=None) -> None:
        super().__init__()
        self.start = start
        self.name = name
        self.body = body
        self.client = client
        self.size = size
        self.request_id = request_id if request_id is not None else next(self.id_generator)
        self.replica = replica
        self.headers = headers

    def __str__(self) -> str:
        return 'FunctionRequest(%d, %s, %s)' % (self.request_id, self.name, self.size)

    def __repr__(self):
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.start) + hash(self.name) + hash(self.request_id)


@dataclass
class FunctionResponse:
    request: FunctionRequest
    request_id: Union[int, str]
    # client that has called
    client: str
    # function name
    name: str
    # response body
    body: str
    # size of the response
    size: int
    # response status code
    code: int
    # timestamp that is taken before any data transfer or execution happened
    # (ts_end - ts_start) -> is the true round trip time of the request, including every latency
    ts_start: float
    # timestamp of waiting to be executed
    ts_wait: float
    # timestamp of starting execution
    ts_exec: float
    # timestamp of ending execution
    ts_end: float
    # raw function execution time, without wait
    fet: float
    # replica which the request was processed
    replica: FunctionReplica
    # node on which the request was processed
    node: FunctionNode




class FaasSystem(abc.ABC):

    @abc.abstractmethod
    def deploy(self, fn: FunctionDeployment):
        """
        Deploys a function in the system.
        It is necessary to deploy a function before invoking, remove, etc. it.
        :param fn: function to deploy
        """
        ...

    @abc.abstractmethod
    def invoke(self, request: Union[FunctionRequest, WorkloadConfiguration]):
        """
        Invokes a function. It depends on the specific type of the argument and the implementation on how this is achieved.
        In general, passing a FunctionRequest will lead to a single invocation while a WorkloadConfiguration will specify
        a lengthy sequence of function invocations.
        :param request: either a single FunctionRequest or a specification as type of WorkloadConfiguration
        """
        ...

    @abc.abstractmethod
    def remove(self, fn: FunctionDeployment):
        """
        Removes the given function.
        This entails shutting down all function replicas. The implementation determines whether running calls are cancelled
        or will wait for all invocations being processed.
        :param fn: function to remove
        """
        ...

    @abc.abstractmethod
    def get_deployments(self) -> List[FunctionDeployment]:
        """
        Fetches all FunctionDeployments that were previously deployed. Does not contain removed deployments
        :return: a list of deployments
        """
        ...

    @abc.abstractmethod
    def get_function_index(self) -> Dict[str, FunctionContainer]:
        """
        Dictionary that contains all deployed FunctionContainer, accessible via the specific image name
        :return: a dict
        """
        ...

    @abc.abstractmethod
    def get_replicas(self, fn_name: str, running: bool = True, state=None) -> List[FunctionReplica]:
        """
        Finds all FunctionReplicas for the given function that are in the given state.
        If the state is None all replica are returned
        :param fn_name: the function name
        :param running: set to true if only RUNNING replicas should be returned or all that are not RUNNING
        :param state: optional, the state the function replicas are in or all if None
        """
        ...

    @abc.abstractmethod
    def scale_down(self, function_name: str, remove: Union[int, List[FunctionReplica]]) -> List[FunctionReplica]:
        """
        Scales down the specified function.
        Depending on argument of remove, either chooses the last 'n' replica that were started or
        shuts down the specific replicas passed.
        :param function_name:  the function to scale down
        :param remove: either a number of FunctionReplica to shut down or a specific list of replicas
        :return: list containing the removed replica
        """
        ...

    @abc.abstractmethod
    def scale_up(self, function_name: str, replicas: Union[int, List[FunctionReplica]]) -> List[FunctionReplica]:
        """
        Scales up the specified function.
        Either creates the given number of replica or uses the list of passed replicas (i.e., the node is None in each replica,
        and the implementation assigns it to one, which can happen asynchronously.
        :param function_name:  the function to scale up
        :param remove: either a number of FunctionReplica to start or a specific list of replicas (which
                       need to be mapped to specific nodes)
        :return: list containing the added replica
        """
        ...

    @abc.abstractmethod
    def discover(self, function: FunctionContainer, running: bool = True, state: FunctionReplicaState = None) -> List[
        FunctionReplica]:
        """
        Finds for a specific FunctionContainer all replicas. I.e., all replica that have the same image as the given
        FunctionContainer.
        If the state is None, returns all replicas.
        :param function:  container to look for FunctionReplica in the given state
        :param running: set to true if only RUNNING replicas should be returned or all that are not RUNNING
        :param state: optional, if replicas should be in a specific state
        :return: a list of replicas in the given state, or if None all
        """
        ...

    @abc.abstractmethod
    def poll_available_replica(self, fn: str, interval: int = 0.5, timeout: int = None) -> Optional[
        List[FunctionReplica]]:
        """
        Blocks and repeatedly checks if running replicas are available for the given function.
        :param fn: the function to poll for
        :param interval: determines in which interval the check should be made
        :param timeout: time to wait, if None waits indefinitely
        :return: None if timeout and no replicas, otherwise the running replicas
        """
        ...
