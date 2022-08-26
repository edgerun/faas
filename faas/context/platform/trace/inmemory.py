import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, TypeVar, Callable, Optional

import pandas as pd

from faas.context.platform.node.api import NodeService
from faas.context.platform.trace.api import TraceService
from faas.system import FunctionResponse
from faas.util.point import PointWindow, Point
from faas.util.rwlock import ReadWriteLock

logger = logging.getLogger(__name__)

I = TypeVar('I', bound=FunctionResponse)


@dataclass
class ResponseRepresentation:
    request_id: int
    ts: float
    function: str
    function_image: str
    replica_id: str
    node: str
    rtt: float
    done: float
    sent: float
    origin_zone: str
    dest_zone: str
    client: str
    status: int


class InMemoryTraceService(TraceService[I]):

    def __init__(self, window_size: int, node_service: NodeService,
                 parser: Callable[[I], Optional[ResponseRepresentation]]):
        self.window_size = window_size
        self.node_service = node_service
        self.parser = parser
        self.requests_per_node: Dict[str, PointWindow[I]] = {}
        self.locks = {}
        # TODO does not support new nodes during experiments
        for node in node_service.get_nodes():
            self.locks[node.name] = ReadWriteLock()

    def get_traces_api_gateway(self, node_name: str, start: float, end: float,
                               response_status: int = None) -> pd.DataFrame:
        gateway = self.node_service.find(node_name)
        if gateway is None:
            nodes = self.node_service.get_nodes_by_name()
            raise ValueError(f"Node {node_name} not found, currently stored: {nodes}")
        zone = gateway.zone
        nodes = self.node_service.find_nodes_in_zone(zone)
        requests = defaultdict(list)
        if len(nodes) == 0:
            logger.info(f'No nodes found in zone {zone}')
        for node in nodes:
            with self.locks[node_name].lock.gen_rlock():
                node_requests = self.requests_per_node.get(node.name)
                if node_requests is None or node_requests.size() == 0:
                    continue

                for req in node_requests.value():
                    if parsed is not None:
                        for key, value in parsed.__dict__.items():
                            requests[key].append(value)
        df = pd.DataFrame(data=requests).sort_values(by='ts')
        df.index = pd.DatetimeIndex(pd.to_datetime(df['ts'], unit='s'))

        df = df[df['ts'] >= start]
        df = df[df['ts'] <= end]
        logger.info(f'After filtering {len(df)} traces left for api gateway {node_name}')
        if response_status is not None:
            df = df[df['status'] == response_status]
            logger.info(f'After filtering out non status: {len(df)}')
        return df

    def add_trace(self, response: I):
        with self.locks[response.node.name].lock.gen_wlock():
            node = response.node.name
            window = self.requests_per_node.get(node, None)
            if window is None:
                self.requests_per_node[node] = PointWindow(self.window_size)
            self.requests_per_node[node].append(Point(response.request.start, response))

    def get_traces_for_function(self, function_name: str, start: float, end: float, zone: str = None,
                                response_status: int = None):
        if zone is not None:
            nodes = self.node_service.find_nodes_in_zone(zone)
        else:
            nodes = self.node_service.get_nodes()
        requests = defaultdict(list)
        for node in nodes:
            node_name = node.name
            with self.locks[node_name].lock.gen_rlock():
                node_requests = self.requests_per_node.get(node_name)
                if node_requests is None or node_requests.size() == 0:
                    continue

                for req in node_requests.value():
                    if req.val.name == function_name:
                        parsed = self.parser(req.val)
                        if parsed is not None:
                            for key, value in parsed.__dict__.items():
                                requests[key].append(value)

        df = pd.DataFrame(data=requests)
        if len(df) == 0:
            return df
        df = df.sort_values(by='ts')
        df.index = pd.DatetimeIndex(pd.to_datetime(df['ts'], unit='s'))

        logger.info(f'Before filtering {len(df)} traces for function {function_name}')
        df = df[df['ts'] >= start]
        df = df[df['ts'] <= end]
        logger.info(f'After filtering {len(df)} traces left for function {function_name}')
        if response_status is not None:
            df = df[df['status'] == response_status]
            logger.info(f'AFter filtering out non status: {len(df)}')
        return df.reset_index(drop=True)

    def get_traces_for_function_image(self, function: str, function_image: str, start: float, end: float,
                                      zone: str = None,
                                      response_status: int = None):
        df = self.get_traces_for_function(function, start, end, zone, response_status)
        df = df[df['function_image'] == function_image]
        return df
