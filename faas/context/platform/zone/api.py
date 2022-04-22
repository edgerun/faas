import abc
from typing import List


class ZoneService(abc.ABC):

    def get_zones(self) -> List[str]:
        """
        Get all zones that are available in the cluster
        :return: a list of zones in the cluster
        """
        raise NotImplementedError()
