import abc
from datetime import datetime
from typing import Dict, Callable, NamedTuple

from faas.system.core import FunctionContainer, FunctionDeployment, FunctionReplica, ScheduleEvent, FunctionReplicaState


class Record(NamedTuple):
    measurement: str
    time: int
    fields: Dict
    tags: Dict


class Clock:
    def now(self) -> datetime:
        raise NotImplementedError()


class WallClock(Clock):

    def now(self) -> datetime:
        return datetime.now()


class MetricsLogger(abc.ABC):
    def log(self, metric, value, time=None, **tags):
        """
        Call l.log('cpu_load', .65, host='server0', region='us-west') or

        :param metric: the name of the measurement
        :param value: the measurement value
        :param time: the (optional) time, otherwise now will be used
        :param tags: additional tags describing the measurement
        :return:
        """
        ...


class NullLogger(MetricsLogger):
    """
    Null logger does nothing.
    """

    def log(self, name, value, time=None, **tags):
        pass


class RuntimeLogger(MetricsLogger):
    def __init__(self, clock=None) -> None:
        self.records = list()
        self.clock = clock or WallClock()

    def get(self, name, **tags):
        return lambda x: self.log(name, x, None, **tags)

    def log(self, metric, value, time=None, **tags):
        """
        Call l.log('cpu_load', .65, host='server0', region='us-west') or

        :param metric: the name of the measurement
        :param value: the measurement value
        :param time: the (optional) time, otherwise now will be used
        :param tags: additional tags describing the measurement
        :return:
        """
        if time is None:
            time = self._now()

        if type(value) == dict:
            fields = value
        else:
            fields = {
                'value': value
            }

        self._store_record(Record(metric, time, fields, tags))

    def _store_record(self, record: Record):
        self.records.append(record)

    def _now(self):
        return self.clock.now()


class PrintLogger(RuntimeLogger):

    def _store_record(self, record: Record):
        super()._store_record(record)
        print('[log]', record)


class LoggingLogger(RuntimeLogger):
    """
    Logger that uses a custom callable
    """

    def __init__(self, logger: Callable[[Dict], None], clock=None):
        super().__init__(clock)
        self.logger = logger

    def _store_record(self, record: Record):
        super()._store_record(record)
        self.logger(record.__dict__)


class Metrics:
    """
    Central logger for system events (i.e., scale down, deploy, remove...).
    Offers pre-defined log functions that are encouraged to use but allows to simply use the log function of the
    logger directly too to guarantee flexibility.
    """

    def __init__(self, log: MetricsLogger = None) -> None:
        super().__init__()
        self.logger: MetricsLogger = log or NullLogger()

    def log(self, metric, value, **tags):
        return self.logger.log(metric, value, **tags)

    def log_function_deployment(self, fn: FunctionDeployment):
        """
        Logs the deployment of a FunctionDeployment. Additionally logs all containers that are contained in it.
        """
        record = {'name': fn.name, 'labels': fn.fn.labels}
        for container in fn.fn_containers:
            self.log_function_containers(fn.name, container)
        self.log('function_deployments', record, type='deploy')

    def log_function_deployment_suspend(self, fn: FunctionDeployment):
        """
        Logs the suspension of a FunctionDeployment
        """
        record = {'name': fn.name, 'labels': fn.fn.labels}
        self.log('function_deployments', record, type='suspend')

    def log_function_deployment_remove(self, fn: FunctionDeployment):
        """
        Logs the removal of a FunctionDeployment
        :param fn:
        :return:
        """
        record = {'name': fn.name, 'labels': fn.fn.labels}
        self.log('function_deployments', record, type='remove')

    def log_function_containers(self, fn_name: str, fn: FunctionContainer):
        """
        Logs the functions name, container image and their metadata
        """
        record = {'name': fn_name, 'image': fn.image, 'labels': fn.labels, 'resource_config': fn.resource_config}
        self.log('functions_containers', record)

    def log_function_replica(self, replica: FunctionReplica, **kwargs):
        """
        Log function to store information about the replica (i.e., function name, image, labels).
        Does not contain any information about the state (see 'log_replica_lifecycle')
        :param replica:
        :return:
        """
        container = replica.container
        record = {'function': replica.function.name, 'labels': replica.labels, 'image': container.image}
        self.log('function_replicas', record, replica_id=replica.replica_id, **kwargs)

    def log_scaling(self, function_name: str, num_replicas: int, **kwargs):
        """
        Log function to indicate a scaling event for a given function.
        Number of replicas indicate how many replicas are started (or teared down in case the number is negative)
        :param function_name:
        :param num_replicas:
        :param kwargs:
        :return:
        """
        self.log('scale', num_replicas, function_name=function_name, **kwargs)

    def log_replica_lifecycle(self, replica: FunctionReplica, event: FunctionReplicaState, **kwargs):
        """
        Use to log if lifecycle events happen.
        Does not contain any info (i.e., container image). Use 'log_function_replica' to save any metadata.
        :param replica: the replica which lifecycle is changed
        :param event: the lifecycle event
        """
        node_name = "None"
        if replica.node is not None:
            node_name = replica.node.name
        self.log('replica_deployment', event, function_name=replica.function.name, node_name=node_name,
                 replica_id=replica.replica_id, **kwargs)

    def log_replica_schedule_event(self, replica: FunctionReplica, event: ScheduleEvent, **kwargs):
        """
        Logs events that revolve around the scheduling phase of a replica.
        :param replica: the replica that is being scheduled
        :param event: the event
        :param kwargs: passed onto the logger to allow extra key-value pairs
        """
        name = replica.fn_name
        image = replica.image
        self.log('schedule', event, function_name=name, image=image,
                 replica_id=replica.replica_id, **kwargs)
