import abc
from typing import Any


class Observer(abc.ABC):

    def fire(self, event: str, value: Any): ...