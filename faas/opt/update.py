from dataclasses import dataclass
from typing import Dict


@dataclass
class OptimizerUpdate:
    args: Dict[str, float]
