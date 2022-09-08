import abc
from typing import Generic, TypeVar, Callable, List

import pandas as pd

from faas.system import FunctionResponse

I = TypeVar('I', bound=FunctionResponse)


class TraceService(abc.ABC, Generic[I]):

    def get_traces_api_gateway(self, node_name: str, start: float, end: float,
                               response_status: int = None) -> pd.DataFrame:
        """
        Returns all traces that were processed in the region the passed api gateway is situated.
        Which means that the API gateway was the last one to forward the request to the compute unit (i.e., Pod)

        DataFrame contains:
            'ts'
            'function'
            'image'
            'container_id'
            'node'
            'rtt'
            'sent'
            'done'
            'origin_zone'
            'dest_zone'
            'client

        :param node_name: the name of the node which hosts the gateway
        :return: DataFrame containing the traces
        """
        ...

    def get_traces_for_function(self, function: str, start: float, end: float, zone: str = None,
                                response_status: int = None):
        """
        Returns all traces that were processed for the given deployment.

        DataFrame contains:
            'ts'
            'function'
            'image'
            'function_replica_id'
            'node'
            'rtt'
            'sent'
            'done'
            'origin_zone'
            'dest_zone'
            'client

        :param function: the function to fetch functions calls from
        :param start: float
        :param end: float
        :param zone: optional, includes only traces that were processed in the given zone (i.e., the executing node was in the zone)
        :param response_status: optional, if None returns all responses otherwise checks for status code
        :return: DataFrame containing the traces
        """
        ...

    def get_values_for_function(self, function: str, start: float, end: float, access: Callable[['ResponseRepresentation'], float], zone: str = None,
                                response_status: int = None):
        """
        Returns all values from traces that were processed for the given deployment.

        :param function: the function to fetch functions calls from
        :param start: float
        :param end: float
        :param zone: optional, includes only traces that were processed in the given zone (i.e., the executing node was in the zone)
        :param response_status: optional, if None returns all responses otherwise checks for status code
        :return: DataFrame containing the traces
        """
        ...

    def get_traces_for_function_image(self, function: str, function_image: str, start: float, end: float,
                                      zone: str = None,
                                      response_status: int = None): ...

    def add_trace(self, response: I):
        ...
