from typing import Tuple, Optional

from scheduler import Scheduler
from object import PriorityType


class MMKP(Scheduler):
    def _init_config(self):
        ...

    def do_assign(self, preemptive: bool) -> Tuple[Optional[Tuple[int, ...]],]:
        pass
