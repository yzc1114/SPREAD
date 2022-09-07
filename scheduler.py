import abc
from abc import ABC
from typing import Optional, Dict, Tuple, Set, Any

from cluster import Cluster, Assignments
from data_source import DataSource
from model import SnapshotRecordParameters
from profit import get_profit_calculator
from object import SchedulerEnum, SolverEnum, ProfitEnum, GPUType, MemoryUnit, CompCapacity, PriorityType


class Scheduler(ABC):
    def __init__(self,
                 name: str,
                 scheduler_enum: SchedulerEnum,
                 solver_enum: Optional[SolverEnum],
                 profit_enum: Optional[ProfitEnum],
                 data_source: DataSource,
                 cluster: Cluster,
                 config: Dict):
        self.name: str = name
        self.scheduler_enum: SchedulerEnum = scheduler_enum
        self.data_source: DataSource = data_source
        self.cluster: Cluster = cluster
        self.solver_enum: Optional[SolverEnum] = solver_enum
        self.profit_enum: Optional[ProfitEnum] = profit_enum
        self.config: Dict = config
        self._init_config()
        self.do_plot: bool = config.get("do_plot", True)
        self.priority_type: PriorityType = PriorityType[self.config.get("priority_type", "FCFS")]
        self.__init_view_data()

    @abc.abstractmethod
    def _init_config(self):
        ...

    def __init_view_data(self):
        self.GPU_type_to_comp_mem_capacity: Dict[GPUType, Tuple[int, int]] = dict()
        self.GPU_type_to_GPU_IDs: Dict[GPUType, Set[str]] = dict()
        for GPU_type, gs in self.cluster.GPUs.items():
            comp, mem = CompCapacity, GPUType.real_memory(GPU_type=GPU_type) // MemoryUnit
            self.GPU_type_to_comp_mem_capacity[GPU_type] = (comp, mem)
            self.GPU_type_to_GPU_IDs[GPU_type] = {g.GPU_ID for g in gs}

    def build_snapshot_record_parameters(self) -> SnapshotRecordParameters:
        # scheduler_name: str
        # scheduler_type: SchedulerEnum
        # solver_type: Optional[SolverEnum]
        # GPU_type_to_GPU_IDs: Dict[GPUType, Set[str]]
        # dist_job_to_tasks: Dict[str, Tuple[str, ...]]
        # task_comp_mem_requirements: Dict[str, Tuple[int, int]]
        # task_comp_over_supply: Dict[str, int]
        # assignments: Dict[str, Set[str]]
        # profit: Union[int, float]
        # do_plot: Optional[bool]

        dist_job_to_tasks: Dict[str, Tuple[str, ...]] = self.cluster.assignments.dist_job_to_tasks()
        task_comp_mem_requirements: Dict[str, Tuple[int, int]] = self.cluster.assignments.task_comp_mem_requirements()
        assignments = self.cluster.assignments.to_solver_assignments()
        job_over_supply, total_over_supply = self.cluster.assignments.get_job_over_supply()
        job_lack_supply, total_lack_supply = self.cluster.assignments.get_job_lack_supply(data_source=self.data_source)
        def job_d_to_task_d(d: Dict[str, int], assignments_: Assignments):
            t_d = dict()
            for job_ID, task_assignments in assignments_.job_ID_to_task_assignments.items():
                worker_count = len(task_assignments)
                for task_assignment in task_assignments:
                    if job_ID in d:
                        t_d[task_assignment.task.task_ID] = d[job_ID] // worker_count
                    else:
                        t_d[task_assignment.task.task_ID] = 0
            return t_d

        task_over_supply = job_d_to_task_d(job_over_supply, assignments_=self.cluster.assignments)
        task_lack_supply = job_d_to_task_d(job_lack_supply, assignments_=self.cluster.assignments)

        return SnapshotRecordParameters(
            scheduler_name=self.name,
            scheduler_type=self.scheduler_enum,
            solver_type=self.solver_enum,
            GPU_type_to_GPU_IDs=self.GPU_type_to_GPU_IDs,
            dist_job_to_tasks=dist_job_to_tasks,
            task_comp_mem_requirements=task_comp_mem_requirements,
            task_comp_over_supply=task_over_supply,
            task_comp_lack_supply=task_lack_supply,
            assignments=assignments,
            profit=self.cluster.assignments.calc_profits(data_source=self.data_source, profit_calculator=get_profit_calculator(self.profit_enum)),
            do_plot=self.do_plot
        )

    @abc.abstractmethod
    def do_assign(self, preemptive: bool) -> Tuple[Assignments, Optional[Any], ]:
        """

        :param preemptive:
        :return:
            Assignments: assignments
            Optional[Any]: any scheduler reports
        """
        ...
