from typing import List

from faas.context import ZoneService


class InMemoryZoneService(ZoneService):

    def __init__(self, zones: List[str]):
        self.zones = zones

    def get_zones(self) -> List[str]:
        return self.zones
