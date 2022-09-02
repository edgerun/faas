import abc
import datetime
from typing import Optional

import pandas as pd


class TelemetryService(abc.ABC):

    def get_replica_cpu(self, fn_replica_id: str, start: float = None, end: float = None) -> \
            Optional[pd.DataFrame]:
        """
        Fetch the measured cpu times for the given replica in the given timeframe.
        If start is None, the start of the selection will be set to 01-01-1970.
        If end is None, the end will be set to now.
        """
        raise NotImplementedError()

    def get_node_cpu(self, node: str, start: float = None, end: float = None) -> Optional[
        pd.DataFrame]:
        raise NotImplementedError()
