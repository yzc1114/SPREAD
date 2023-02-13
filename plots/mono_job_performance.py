import math
from typing import Tuple

from mono_job_data_preprocess import *

grid_plot_font = 24
grid_plot_row = 2
grid_plot_col = 4
grid_plot_width = 32
grid_plot_height = 7
grid_plot_legend_pot = (0.01, 0.897)
grid_plot_top = 0.78


def plot_mono_job_performance(ax, model_name: ModelName,
                              exec_infos: List[JobExecInfo]):
    marker_legend_handles = list()
    batch_size_set = set()
    exec_infos = MonoJobExecInfoLoader.extract(exec_infos)
    batch_sizes = sorted(MonoJobExecInfoLoader.batch_sizes(exec_infos))[2:]
    min_batch_size = batch_sizes[0]
    max_batch_size = batch_sizes[2]
    acc_type_to_batch_size_to_performance = dict()
    for acc_type in AccType:
        acc_exec_infos = MonoJobExecInfoLoader.extract_acc_type_with(exec_infos, acc_type=acc_type)
        batch_sizes = MonoJobExecInfoLoader.batch_sizes(acc_exec_infos)
        batch_sizes = list(filter(lambda bs: min_batch_size <= bs <= max_batch_size, batch_sizes))
        batch_size_set = batch_size_set.union(batch_sizes)
        marker_legend_handle = mlines.Line2D([], [],
                                             color='black',
                                             marker=acc_type.value.marker,
                                             linestyle=acc_type.value.line,
                                             label=f"{acc_type.value.name}")
        # ax.plot(x_range, np.arange(1, 21) / 20.,
        #         linestyle=":",
        #         linewidth='4',
        #         color="black")
        marker_legend_handles.append(marker_legend_handle)
        for i, batch_size in enumerate(batch_sizes):
            iteration_intervals = list()
            for comp in range(10, 210, 10):
                worker_count = math.ceil(comp / 100)
                single_worker_comp = comp // worker_count
                single_worker_batch_size = batch_size // worker_count
                info = MonoJobExecInfoLoader.extract(infos=acc_exec_infos, worker_count=1,
                                                     batch_size=single_worker_batch_size,
                                                     computation_proportion_predicate=lambda c: c == single_worker_comp)
                if len(info) == 1:
                    iteration_interval = info[0].avg_stabled_iteration_interval
                else:
                    l = MonoJobExecInfoLoader.extract(infos=acc_exec_infos, worker_count=1,
                                                      batch_size=single_worker_batch_size,
                                                      computation_proportion_predicate=lambda
                                                          c: c == single_worker_comp - 5)
                    r = MonoJobExecInfoLoader.extract(infos=acc_exec_infos, worker_count=1,
                                                      batch_size=single_worker_batch_size,
                                                      computation_proportion_predicate=lambda
                                                          c: c == single_worker_comp + 5)
                    iteration_interval = (l[0].avg_stabled_iteration_interval + r[0].avg_stabled_iteration_interval) / 2
                if worker_count > 1:
                    # plus communication overhead
                    iteration_interval += get_communication_overhead(exec_infos=exec_infos, batch_size=batch_size,
                                                                     worker_count=worker_count)
                iteration_intervals.append(iteration_interval)
            iteration_intervals = np.array(iteration_intervals, dtype=np.float)
            iteration_intervals /= 1e9
            # normalized_performances = np.min(iteration_intervals) / iteration_intervals
            normalized_performances = 1 / iteration_intervals
            acc_type_to_batch_size_to_performance.setdefault(acc_type, dict())
            acc_type_to_batch_size_to_performance[acc_type].setdefault(batch_size, normalized_performances)

    maximum_performance = 0
    for bs_to_performances in acc_type_to_batch_size_to_performance.values():
        for performances in bs_to_performances.values():
            maximum_performance = max(max(performances), maximum_performance)

    for acc_type in AccType:
        acc_exec_infos = MonoJobExecInfoLoader.extract_acc_type_with(exec_infos, acc_type=acc_type)
        batch_sizes = MonoJobExecInfoLoader.batch_sizes(acc_exec_infos)
        batch_sizes = list(filter(lambda bs: min_batch_size <= bs <= max_batch_size, batch_sizes))
        for batch_size in batch_sizes:
            x_range = np.arange(10, 210, step=10)
            normalized_performances = acc_type_to_batch_size_to_performance[acc_type][batch_size] / maximum_performance
            ax.plot(x_range, normalized_performances,
                    marker=acc_type.value.marker,
                    linestyle=acc_type.value.line,
                    linewidth='1',
                    label=f"{acc_type.value.name} ({batch_size})",
                    color=batch_size_color(batch_size))
    color_legend_handles = list()
    batch_sizes = sorted(list(batch_size_set))
    for i, batch_size in enumerate(batch_sizes):
        handle = mlines.Line2D([], [],
                               marker="s",
                               linestyle="None",
                               label=rf"bs. {i + 1} $\times$",
                               color=batch_size_color(batch_size))
        color_legend_handles.append(handle)
    # lg1 = ax.legend(handles=marker_legend_handles, loc=2)
    # lg2 = ax.legend(handles=color_legend_handles, loc=4)
    # ax.add_artist(lg1)
    # ax.add_artist(lg2)
    inside_ticks(ax=ax, x=True, y=True)
    ax.set_yticks([0, 0.5, 1])
    ax.yaxis.set_major_formatter(plt_ticker.FuncFormatter('{0:.0%}'.format))
    ax.yaxis.grid(True)
    ax.xaxis.grid(True)

    # inside_ticks(ax)
    ax.set_xlabel(f'Comp. Resource (%)')
    ax.set_title(f'{model_name.name}')
    ax.set_ylabel('Performance')
    return marker_legend_handles + color_legend_handles


def plot_mono_job_performance_with_diff_worker_count(ax, model_name: ModelName,
                                                     worker_counts: Tuple[int, ...],
                                                     acc_type: AccType,
                                                     exec_infos: List[JobExecInfo]):
    marker_legend_handles = list()
    batch_size_set = set()
    StyleSpec = namedtuple(typename="StyleSpec", field_names="line marker label")
    worker_count_to_specs = {
        1: StyleSpec("-", "o", "1 sub-job"),
        2: StyleSpec("--", "^", "2 sub-jobs")
    }
    for worker_count in worker_counts:
        acc_exec_infos = MonoJobExecInfoLoader.extract_acc_type_with(exec_infos, acc_type=acc_type)
        batch_sizes = MonoJobExecInfoLoader.batch_sizes(acc_exec_infos)
        batch_sizes = batch_sizes[2:]
        batch_size_set = batch_size_set.union(batch_sizes)
        x_range = np.arange(5, 105, step=5)
        spec = worker_count_to_specs[worker_count]
        marker_legend_handle = mlines.Line2D([], [],
                                             color='black',
                                             marker=spec.marker,
                                             linestyle=spec.line,
                                             label=spec.label)
        ax.plot(x_range, np.arange(5, 105, step=5) / 100.,
                linestyle=":",
                linewidth='4',
                color="black")
        marker_legend_handles.append(marker_legend_handle)
        for i, batch_size in enumerate(batch_sizes):
            infos = MonoJobExecInfoLoader.extract(infos=acc_exec_infos, batch_size=batch_size,
                                                  worker_count=worker_count)
            infos = MonoJobExecInfoLoader.sort_by_computation(infos)
            assert len(infos) == 20
            intervals = [info.avg_stabled_iteration_interval for info in infos]
            min_interval = min(intervals)
            normalized_performance = [float(min_interval / interval) for interval in intervals]
            ax.plot(x_range, normalized_performance,
                    marker=spec.marker,
                    linestyle=spec.line,
                    linewidth='1',
                    color=batch_size_color(batch_size))
    color_legend_handles = list()
    batch_sizes = sorted(list(batch_size_set))
    for batch_size in batch_sizes:
        handle = mlines.Line2D([], [],
                               marker="s",
                               linestyle="None",
                               label=f"bs. {batch_size}",
                               color=batch_size_color(batch_size))
        color_legend_handles.append(handle)
    lg1 = ax.legend(handles=marker_legend_handles, loc=2)
    lg2 = ax.legend(handles=color_legend_handles, loc=4)
    ax.add_artist(lg1)
    ax.add_artist(lg2)
    inside_ticks(ax=ax, x=True, y=True)
    ax.yaxis.grid(True)
    ax.xaxis.grid(True)
    ax.yaxis.set_major_formatter(plt_ticker.FuncFormatter('{0:.0%}'.format))

    # inside_ticks(ax)
    ax.set_xlabel(f'Comp. Quota (%)')
    ax.set_title(f'{model_name.name}')
    ax.set_ylabel('Performance')


def plot_mono_jobs_diff_worker_count_performance(mono_job_exec_infos: Dict[ModelName, List[JobExecInfo]]):
    original_fontsize = mpl.rcParams["font.size"]
    mpl.rcParams.update({'font.size': 21})
    col = grid_plot_col
    row = grid_plot_row
    fig, axes = plt.subplots(row, col, figsize=(32, 8))

    handles = None
    acc_type = AccType.RTX_2080Ti
    for i, item in enumerate(mono_job_exec_infos.items()):
        model_name, exec_infos = item
        infos = MonoJobExecInfoLoader.extract(exec_infos,
                                              train_or_inference=TrainOrInference.train,
                                              acc_type=acc_type)
        plot_mono_job_performance_with_diff_worker_count(axes[i // col, i % col],
                                                         model_name,
                                                         worker_counts=(1, 2),
                                                         acc_type=acc_type,
                                                         exec_infos=infos)
        # new_handles = plot_mono_job_dist_performance(axes[i % col], model_name, exec_infos, acc_type, comps=comps)
        # if handles is None:
        #     handles = new_handles
    fig.tight_layout()
    # lgd = fig.legend(handles=handles, loc=(0, 0.81), ncol=len(handles))
    # lgd.get_frame().set_alpha(None)
    # fig.suptitle(f"Training Performance with Different Computation Quotas", fontsize="x-large")
    fig.subplots_adjust(top=grid_plot_top)
    save_fig(fig, output_path(f"mono_job_performance_diff_quotas.pdf"))
    mpl.rcParams.update({'font.size': original_fontsize})


def plot_mono_jobs_performance(mono_job_exec_infos: Dict[ModelName, List[JobExecInfo]]):
    original_fontsize = mpl.rcParams["font.size"]
    mpl.rcParams.update({'font.size': 24})
    col = grid_plot_col
    row = grid_plot_row
    fig, axes = plt.subplots(row, col, figsize=(32, 8))

    handles = None
    for i, item in enumerate(mono_job_exec_infos.items()):
        model_name, exec_infos = item
        new_handles = plot_mono_job_performance(axes[i // col, i % col], model_name, exec_infos)
        if handles is None or len(new_handles) > len(handles):
            handles = new_handles
    lgd = fig.legend(handles=handles, loc=grid_plot_legend_pot, ncol=len(handles))
    lgd.get_frame().set_alpha(None)
    fig.tight_layout()
    fig.subplots_adjust(top=grid_plot_top)
    save_fig(fig, output_path(f"mono_job_performance_diff_comps.pdf"))
    mpl.rcParams.update({'font.size': original_fontsize})


def plot_mono_jobs_memory(mono_job_exec_infos: Dict[ModelName, List[JobExecInfo]],
                          train_or_inference: TrainOrInference):
    fig, ax = plt.subplots(figsize=(10, 4))
    labels = [model_name.name for model_name in ModelName]

    batch_size_level_to_model_to_memory = defaultdict(dict)
    for model_name in ModelName:
        exec_infos = mono_job_exec_infos[model_name]
        exec_infos = MonoJobExecInfoLoader.extract(exec_infos, train_or_inference=train_or_inference,
                                                   acc_type=AccType.RTX_2080Ti, worker_count=1)
        batch_sizes = MonoJobExecInfoLoader.batch_sizes(exec_infos)
        for i, batch_size in enumerate(batch_sizes):
            same_batch_size_infos = MonoJobExecInfoLoader.extract(exec_infos, batch_size=batch_size)
            memory_consumption = most([info.most_memory_consumption for info in same_batch_size_infos])
            batch_size_level_to_model_to_memory[i][model_name] = memory_consumption / GBi
    max_batch_size_level = len(batch_size_level_to_model_to_memory)
    batch_size_level_to_memory_list = dict()
    for batch_size_level in range(max_batch_size_level):
        model_to_memory = batch_size_level_to_model_to_memory[batch_size_level]
        model_memory_list = [model_to_memory.get(model_name, 0) for model_name in ModelName]
        batch_size_level_to_memory_list[batch_size_level] = np.array(model_memory_list)
    for batch_size_level in reversed(range(max_batch_size_level)):
        if batch_size_level - 1 >= 0:
            batch_size_level_to_memory_list[batch_size_level] -= batch_size_level_to_memory_list[batch_size_level - 1]
            batch_size_level_to_memory_list[batch_size_level] = batch_size_level_to_memory_list[batch_size_level].clip(
                min=0)
    for batch_size_level in range(max_batch_size_level):
        y = batch_size_level_to_memory_list[batch_size_level]
        minor_y = np.zeros_like(y)
        for minor_batch_size_level in range(batch_size_level):
            minor_y += batch_size_level_to_memory_list[minor_batch_size_level]
        ax.bar(labels, y, width=0.3, bottom=minor_y, color=batch_size_level_color(batch_size_level))

    ax.yaxis.grid(True)
    ax.set_xlabel("Models")
    ax.set_ylabel("Memory Consumption (GBi)")
    ax.legend([rf"$bs. {2 ** level} \times$" for level in range(max_batch_size_level)], loc=[0.2, 0.45])
    for bars in ax.containers:
        values = ["%.2f" % value if value > 0 else "" for value in bars.datavalues]
        ax.bar_label(bars, labels=values, label_type="center", fontsize=6)
    # ax.set_title("Memory")
    save_fig(fig, output_path(f"mono_job_{train_or_inference.name}_memories.pdf"))


def plot_mono_job_memory_spread_compare(ax,
                                        model_name: ModelName,
                                        exec_infos: List[JobExecInfo],
                                        acc_type: AccType,
                                        worker_counts: Tuple[int, int, int],
                                        ):
    worker_count_to_spreading_label = {
        1: "1 sub-job (No spreading)",
        2: "Spread to 2 sub-jobs",
        4: "Spread to 4 sub-jobs"
    }
    worker_counts_specs = [('local', worker_counts[0], 0, 0),  # comp, dist or local, worker_count, idx, color_idx
                           ('dist_0', worker_counts[1], 0, 1),
                           ('dist_1', worker_counts[2], 0, 2)]
    exec_infos = MonoJobExecInfoLoader.extract(exec_infos, train_or_inference=TrainOrInference.train)
    # local_comp_to_diff_bs_overhead = defaultdict(list)
    local_worker_count_to_diff_bs_mem = defaultdict(list)
    # idx_to_dist_comp_to_diff_bs_overhead = defaultdict(lambda :defaultdict(list))
    idx_to_worker_count_to_diff_bs_mem = defaultdict(lambda: defaultdict(list))
    batch_size_set = MonoJobExecInfoLoader.batch_sizes(MonoJobExecInfoLoader.extract(exec_infos, worker_count=1))
    batch_sizes = sorted(list(batch_size_set))
    batch_sizes = batch_sizes[2:]
    acc_exec_infos = MonoJobExecInfoLoader.extract_acc_type_with(exec_infos, acc_type=acc_type)
    for worker_count_spec in worker_counts_specs:
        local_or_dist, worker_count, idx, _ = worker_count_spec
        local = local_or_dist == "local"
        comp_exec_infos = MonoJobExecInfoLoader.extract(acc_exec_infos,
                                                        computation_proportion_predicate=lambda cp: cp == 50,
                                                        worker_count=1)
        for i, batch_size in enumerate(batch_sizes):
            batch_size //= worker_count
            info = MonoJobExecInfoLoader.extract(infos=comp_exec_infos, batch_size=batch_size)
            local_info = MonoJobExecInfoLoader.extract(infos=comp_exec_infos, batch_size=int(batch_size * worker_count))
            assert len(info) == 1
            assert len(local_info) == 1
            info = info[0]
            local_info = local_info[0]
            curr_mem = info.most_memory_consumption
            if worker_count == 1:
                local_worker_count_to_diff_bs_mem[worker_count].append(
                    (info.most_memory_consumption, 1.0))
            else:
                standard_mem = local_info.most_memory_consumption
                mem_proportion = curr_mem / standard_mem
                idx_to_worker_count_to_diff_bs_mem[idx][worker_count].append(
                    (curr_mem, mem_proportion))

    print(f"{model_name}", local_worker_count_to_diff_bs_mem)
    print(f"{model_name}", idx_to_worker_count_to_diff_bs_mem)

    N = len(batch_sizes)
    ind = np.arange(N)
    width = 0.25

    performance_bar_legend_artists = list()
    performance_bars = list()
    local_hatch = r"/"
    dist_hatches = [r"*", r"o"]
    edgecolor = None

    for i, worker_count_spec in enumerate(worker_counts_specs):
        local_or_dist, worker_count, idx, color_idx = worker_count_spec
        local = local_or_dist == "local"
        worker_count_to_diff_bs_mem = local_worker_count_to_diff_bs_mem if local else \
            idx_to_worker_count_to_diff_bs_mem[idx]
        diff_bs_mem = worker_count_to_diff_bs_mem[worker_count]
        normalized_mem = np.array([p[-1] for p in diff_bs_mem])
        # GPU_label = f"{worker_count} GPU"
        spreading_label = worker_count_to_spreading_label[worker_count]
        spreading_color = colors[color_idx]
        if local:
            hatch = local_hatch
        else:
            hatch = dist_hatches[int(local_or_dist.split("_")[-1])]
        performance_bars.append(ax.bar(
            ind + i * width,
            normalized_mem,
            edgecolor=edgecolor,
            width=width,
            color=spreading_color,
            label=spreading_label,
            hatch=hatch
        ))
        handle = Patch(
            facecolor=spreading_color,
            edgecolor=edgecolor,
            label=spreading_label,
            hatch=hatch
        )
        performance_bar_legend_artists.append(handle)
    ax.set_xlabel(f"Batch Sizes")
    ax.set_title(f"{model_name.name}")
    ax.set_ylabel('Memory')
    ax.set_xticks(ind + (len(worker_counts_specs) - 1) / 2 * width, [str(bs) for bs in batch_sizes])
    ax.set_yticks([0, 0.25, 0.5, 1])
    ax.yaxis.grid(True)
    ax.yaxis.set_major_formatter(plt_ticker.FuncFormatter('{0:.0%}'.format))
    return performance_bar_legend_artists


def plot_mono_jobs_memory_spread_compare(mono_job_exec_infos: Dict[ModelName, List[JobExecInfo]]):
    original_fontsize = mpl.rcParams["font.size"]
    mpl.rcParams.update({'font.size': grid_plot_font})
    col = grid_plot_col
    row = grid_plot_row
    fig, axes = plt.subplots(row, col, figsize=(grid_plot_width, grid_plot_height))

    handles = None
    acc_type = AccType.RTX_2080Ti
    for i, item in enumerate(mono_job_exec_infos.items()):
        model_name, exec_infos = item
        new_handles = plot_mono_job_memory_spread_compare(axes[i // col, i % col], model_name, exec_infos, acc_type,
                                                          worker_counts=(1, 2, 4))
        if handles is None:
            handles = new_handles
    fig.tight_layout()
    lgd = fig.legend(handles=handles, loc=grid_plot_legend_pot, ncol=len(handles))
    lgd.get_frame().set_alpha(None)
    # fig.suptitle(f"Memory Quotas of Workers With Various Spreading Configurations", fontsize="x-large")
    fig.subplots_adjust(top=0.83)
    # fig.show()
    fig.savefig(output_path(f"mono_job_dist_memory.pdf"), dpi=400, format='pdf', bbox_inches='tight')
    mpl.rcParams.update({'font.size': original_fontsize})


def get_communication_overhead(exec_infos: List[JobExecInfo], batch_size: int, worker_count: int):
    local_50 = MonoJobExecInfoLoader.extract(exec_infos, batch_size=batch_size, acc_type=AccType.RTX_2080Ti,
                                             worker_count=1,
                                             computation_proportion_predicate=lambda cp: cp == 50)
    dist_50 = MonoJobExecInfoLoader.extract(exec_infos, batch_size=batch_size, acc_type=AccType.RTX_2080Ti,
                                            worker_count=worker_count,
                                            computation_proportion_predicate=lambda cp: cp == 50)
    overhead = dist_50[0].avg_stabled_iteration_interval - local_50[0].avg_stabled_iteration_interval
    return overhead


def plot_mono_job_dist_performance(ax,
                                   model_name: ModelName,
                                   exec_infos: List[JobExecInfo],
                                   acc_type: AccType,
                                   comps: Tuple[int, int, int, int, int] = (100, 50, 60, 25, 30)
                                   ):
    computation_proportions = [(comps[0], 'local', 1, 0, 0),  # comp, dist or local, worker_count, idx, color_idx
                               (comps[1], 'dist_0', 2, 0, 1),
                               (comps[2], 'dist_1', 2, 0, 2),
                               (comps[3], 'dist_2', 4, 0, 3),
                               (comps[4], 'dist_3', 4, 0, 4),
                               ]
    exec_infos = MonoJobExecInfoLoader.extract(exec_infos, train_or_inference=TrainOrInference.train)
    local_comp_to_diff_bs_overhead = defaultdict(list)
    local_comp_to_diff_bs_performance = defaultdict(list)
    idx_to_dist_comp_to_diff_bs_overhead = defaultdict(lambda: defaultdict(list))
    idx_to_dist_comp_to_diff_bs_performance = defaultdict(lambda: defaultdict(list))
    batch_size_set = MonoJobExecInfoLoader.batch_sizes(MonoJobExecInfoLoader.extract(exec_infos, worker_count=1))
    batch_sizes = sorted(list(batch_size_set))
    batch_sizes = batch_sizes[2:]
    acc_exec_infos = MonoJobExecInfoLoader.extract_acc_type_with(exec_infos, acc_type=acc_type)
    for computation_proportion in computation_proportions:
        comp, local_or_dist, worker_count, idx, _ = computation_proportion
        local = local_or_dist == "local"
        if local and comp in local_comp_to_diff_bs_performance:
            continue
        comp_exec_infos = MonoJobExecInfoLoader.extract(acc_exec_infos,
                                                        computation_proportion_predicate=lambda cp: cp == comp,
                                                        worker_count=worker_count)
        local_comp_exec_infos = MonoJobExecInfoLoader.extract(acc_exec_infos,
                                                              computation_proportion_predicate=lambda cp: cp == comp,
                                                              worker_count=1)
        for i, batch_size in enumerate(batch_sizes):
            batch_size //= worker_count
            info = MonoJobExecInfoLoader.extract(infos=comp_exec_infos, batch_size=batch_size)
            local_info = MonoJobExecInfoLoader.extract(infos=local_comp_exec_infos, batch_size=batch_size)
            assert len(info) == 1
            assert len(local_info) == 1
            info = info[0]
            curr_performance = info.avg_stabled_iteration_interval
            local_iteration_interval = local_info[0].avg_stabled_iteration_interval
            overhead = curr_performance - local_iteration_interval
            if overhead < 0:
                overhead = curr_performance * 0.005
            if worker_count == 1:
                local_comp_to_diff_bs_performance[comp].append(
                    (info.avg_stabled_iteration_interval, 1.0))
                local_comp_to_diff_bs_overhead[comp].append(
                    (0, 0.))
            else:
                standard_performance = None
                for cp in computation_proportions:
                    other_comp, other_local_or_dist, _, other_idx, _ = cp
                    if other_idx == idx and other_local_or_dist == "local":
                        standard_performance, _ = local_comp_to_diff_bs_performance[other_comp][i]
                        break
                assert standard_performance is not None
                normalized_performance = standard_performance / curr_performance
                idx_to_dist_comp_to_diff_bs_performance[idx][comp].append(
                    (curr_performance, normalized_performance))
                idx_to_dist_comp_to_diff_bs_overhead[idx][comp].append(
                    (overhead, overhead / curr_performance)
                )

    print(f"{model_name}", local_comp_to_diff_bs_performance)
    print(f"{model_name}", local_comp_to_diff_bs_overhead)
    print(f"{model_name}", idx_to_dist_comp_to_diff_bs_performance)
    print(f"{model_name}", idx_to_dist_comp_to_diff_bs_overhead)

    N = len(batch_sizes)
    ind = np.arange(N)
    width = 0.17

    overhead_bar_legend_artist_list = list()
    performance_bar_legend_artists = list()
    overhead_bars = list()
    performance_bars = list()
    local_hatch = r"/"
    dist_hatches = [r"/", r"/", "/", "/"]
    edgecolor = None

    ax_overhead = ax.twinx()
    ax_overhead.set_ylim([0., 1.])
    ax_overhead_ylabel = "Comm. Overhead"
    # fontsize = 24
    ax_overhead.set_ylabel(ax_overhead_ylabel)
    overhead_linestyle = "--"
    overhead_marker = "*"
    overhead_marker_size = 10
    overhead_linewidth = "4"
    overhead_bar_legend_artist = mlines.Line2D(
        [], [],
        linestyle=overhead_linestyle,
        linewidth=overhead_linewidth,
        marker=overhead_marker,
        markersize=overhead_marker_size,
        label=ax_overhead_ylabel,
        color="black"
    )
    overhead_bar_legend_artist_list.append(overhead_bar_legend_artist)
    for i, computation_proportion in enumerate(computation_proportions):
        comp, local_or_dist, worker_count, idx, color_idx = computation_proportion
        local = local_or_dist == "local"
        comp_to_diff_bs_overhead = local_comp_to_diff_bs_overhead if local else idx_to_dist_comp_to_diff_bs_overhead[
            idx]
        comp_to_diff_bs_performance = local_comp_to_diff_bs_performance if local else \
            idx_to_dist_comp_to_diff_bs_performance[idx]
        diff_bs_overhead = comp_to_diff_bs_overhead[comp]
        diff_bs_performance = comp_to_diff_bs_performance[comp]
        normalized_overheads = np.array([o[-1] for o in diff_bs_overhead])
        normalized_performances = np.array([p[-1] for p in diff_bs_performance])
        overhead_bar_color = colors[color_idx]
        if local_or_dist != "local":
            overhead_bars.append(ax_overhead.plot(
                ind + i * width,
                normalized_overheads,
                linestyle=overhead_linestyle,
                linewidth=overhead_linewidth,
                marker=overhead_marker,
                markersize=overhead_marker_size,
                mfc=overhead_bar_color,
                mec='black',
                color=overhead_bar_color,
                label=ax_overhead_ylabel,
            ))
        performance_label = f"{worker_count} sub-job {comp}% comp." if worker_count == 1 else f"{worker_count} sub-jobs {comp}% comp."
        performance_color = colors[color_idx]
        if local:
            hatch = local_hatch
        else:
            hatch = dist_hatches[int(local_or_dist.split("_")[-1])]
        performance_bars.append(ax.bar(
            ind + i * width,
            normalized_performances,
            edgecolor=edgecolor,
            width=width,
            color=performance_color,
            label=performance_label,
            hatch=hatch
        ))
        handle = Patch(
            facecolor=performance_color,
            edgecolor=edgecolor,
            label=performance_label,
            hatch=hatch
        )
        performance_bar_legend_artists.append(handle)
    ax.set_xlabel(f"Batch Sizes")
    ax.set_title(f'{model_name.name}')
    ax.set_ylabel('Performance')
    ax.set_xticks(ind + (len(computation_proportions) - 1) / 2 * width, [str(bs) for bs in batch_sizes])
    ax.set_yticks([0, 0.5, 1])
    ax.yaxis.grid(True)
    ax.yaxis.set_major_formatter(plt_ticker.FuncFormatter('{0:.0%}'.format))
    ax_overhead.yaxis.set_major_formatter(plt_ticker.FuncFormatter('{0:.0%}'.format))
    return performance_bar_legend_artists + overhead_bar_legend_artist_list


def plot_mono_jobs_dist_performance(mono_job_exec_infos: Dict[ModelName, List[JobExecInfo]], comps):
    original_fontsize = mpl.rcParams["font.size"]
    mpl.rcParams.update({'font.size': grid_plot_font})
    col = grid_plot_col
    row = grid_plot_row
    fig, axes = plt.subplots(row, col, figsize=(grid_plot_width, grid_plot_height))

    handles = None
    acc_type = AccType.RTX_2080Ti
    for i, item in enumerate(mono_job_exec_infos.items()):
        model_name, exec_infos = item
        new_handles = plot_mono_job_dist_performance(axes[i // col, i % col], model_name, exec_infos, acc_type, comps)
        if handles is None:
            handles = new_handles
    fig.tight_layout()
    lgd = fig.legend(handles=handles, loc=grid_plot_legend_pot, ncol=len(handles))
    lgd.get_frame().set_alpha(None)
    # fig.suptitle(f"Training Performance With Various Spreading Configurations (Requesting {comps[0]}% Computation Quota)", fontsize="x-large")
    fig.subplots_adjust(top=grid_plot_top)
    # fig.show()
    fig.savefig(output_path(f"mono_job_dist_performance_{comps[0]}.pdf"), dpi=400, format='pdf', bbox_inches='tight')
    # save_fig(fig, output_path(f"mono_job_dist_performance.pdf"))
    mpl.rcParams.update({'font.size': original_fontsize})


def main():
    mono_job_exec_infos = MonoJobExecInfoLoader.load_infos("./datas/mono_data")

    plot_mono_jobs_memory_spread_compare(mono_job_exec_infos)

    # plot_mono_jobs_diff_worker_count_performance(mono_job_exec_infos)
    plot_mono_jobs_performance(mono_job_exec_infos)

    plot_mono_jobs_dist_performance(mono_job_exec_infos, comps=(100, 50, 60, 25, 30))
    plot_mono_jobs_dist_performance(mono_job_exec_infos, comps=(80, 40, 50, 20, 25))
    plot_mono_jobs_dist_performance(mono_job_exec_infos, comps=(60, 30, 40, 15, 20))
    # plot_mono_jobs_performance(mono_job_exec_infos, train_or_inference=TrainOrInference.inference)
    # plot_mono_jobs_memory(mono_job_exec_infos, train_or_inference=TrainOrInference.inference)


if __name__ == '__main__':
    main()