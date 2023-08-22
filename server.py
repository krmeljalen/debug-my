#!/usr/bin/env python3
import os
import sys
import time
import psutil
import multiprocessing

#
# Threshold settings
#

# CPU thresholds
cpu_usage_threshold_pct = 80  # Percent
cpu_iowait_threshold_pct = 10  # Percent
cpu_steal_threshold_pct = 1  # Percent
cpu_ctx_switches_threshold = 5000  # Per second
cpu_interrupts_threshold = 2000  # Per second

# Memory thresholds
memory_available_threshold = 20  # Percent
swap_usage_threshold = 0  # Bytes
paging_threshold = 0  # Per second

#
# Stdout helpers
#


def header(msg):
    print("========================= {} =========================".format(msg))


def warning(msg):
    print("[WARN] {}".format(msg))


def info(msg):
    print("[INFO] {}".format(msg))


#
# Helper functions
#

# CPU helpers


def get_system_load():
    with open("/proc/loadavg", "r") as f:
        return f.read().split()


def get_cpu_count():
    return multiprocessing.cpu_count()


def get_cpu_usage():
    cpu_percent = psutil.cpu_percent(interval=2)  # Get CPU usage for the last 2 seconds
    return cpu_percent


def get_cpu_performance():
    cpu_data = {}
    # scputimes(user=2.1, nice=0.0, system=1.7, idle=96.2, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0)
    cpu_data["cpu_times"] = psutil.cpu_times_percent()
    # scpustats(ctx_switches=26570269, interrupts=17106030, soft_interrupts=8205427, syscalls=0)
    cpu_data["cpu_stats"] = psutil.cpu_stats()
    return cpu_data


# Memory helpers


def get_memory_stats():
    # svmem(total=8195940352, available=5540249600, percent=32.4, used=2006110208, free=1421676544, active=2616713216, inactive=3336273920, buffers=611999744, cached=4156153856, shared=352309248, slab=439496704)
    memory_data = {}
    memory_data["memory_usage"] = psutil.virtual_memory()
    memory_data["swap_usage"] = psutil.swap_memory()
    return memory_data


def get_paging_stats():
    paging_data = {"pages_in": 0, "pages_out": 0}
    with open("/proc/vmstat", "r") as f:
        for line in f:
            if "pswpin" in line:
                paging_data["pages_in"] = int(line.split()[1])
            elif "pswpout" in line:
                paging_data["pages_out"] = int(line.split()[1])
    return paging_data


#
# Report functions
#


def report_server_load():
    cpu_count = get_cpu_count()
    system_loads = get_system_load()

    for system_load in system_loads[:3]:
        if float(system_load) > cpu_count:
            warning(
                "Server load too high! ({} > {})".format(
                    ", ".join(system_loads[:3]), cpu_count
                )
            )
            return

    # Default response
    info("Server load is fine, below {} cpu cores.".format(cpu_count))


def report_cpu_usage():
    cpu_usage = get_cpu_usage()
    if cpu_usage > cpu_usage_threshold_pct:
        warning(
            "Server CPU usage is too high! ({}% > {}%)".format(
                round(cpu_usage), cpu_usage_threshold_pct
            )
        )
        return

    info(
        "Server CPU usage looks fine. ({}% < {}%)".format(
            round(cpu_usage), cpu_usage_threshold_pct
        )
    )


def report_cpu_performance():
    cpu_performance_stats = get_cpu_performance()

    # IO Wait
    if cpu_performance_stats["cpu_times"].iowait > cpu_iowait_threshold_pct:
        warning(
            "IO wait is high! ({}% > {}%) This means you are doing a lot of network or disk operations that CPU is waiting to finish.".format(
                cpu_performance_stats["cpu_times"].iowait, cpu_iowait_threshold_pct
            )
        )

    # Steal time
    if cpu_performance_stats["cpu_times"].steal > 1:
        warning(
            "CPU Steal detected! ({}% > {}%) Other VMs on particular host are affecting this server CPU resources. Try moving VM to another host that is not overloaded.".format(
                cpu_performance_stats["cpu_times"].steal, cpu_steal_threshold_pct
            )
        )

    cpu_stats_1 = get_cpu_performance()
    time.sleep(1)
    cpu_stats_2 = get_cpu_performance()

    # Context switches
    ctx_switches_per_second = (
        cpu_stats_2["cpu_stats"].ctx_switches - cpu_stats_1["cpu_stats"].ctx_switches
    )
    if ctx_switches_per_second > cpu_ctx_switches_threshold:
        warning(
            "CPU is doing high amount of context switching. (~{}/s > {}/s) Try pinning running processes to specific cores or spearate part of application logic to another server.".format(
                ctx_switches_per_second, cpu_ctx_switches_threshold
            )
        )

    # Interrupts
    interrupts_per_second = (
        cpu_stats_2["cpu_stats"].interrupts - cpu_stats_1["cpu_stats"].interrupts
    )
    if interrupts_per_second > cpu_interrupts_threshold:
        warning(
            "CPU is being often interrupted by hardware events. (~{}/s > {}/s)".format(
                interrupts_per_second, cpu_interrupts_threshold
            )
        )

    # Cache hit ratio
    # Cannot be retrieved without `perf` tool
    return


def report_memory_usage():
    memory_stats = get_memory_stats()

    # Memory usage
    available_mem_pct = round(
        memory_stats["memory_usage"].available
        / memory_stats["memory_usage"].total
        * 100
    )
    if available_mem_pct < memory_available_threshold:
        warning(
            "Available memory is low! ({}% < {}%)".format(
                available_mem_pct, memory_available_threshold
            )
        )

    # Swap usage
    if memory_stats["swap_usage"].used > swap_usage_threshold:
        warning(
            "Server was swapping at one point! ({} > {}) Consider adding more memory to the server.".format(
                psutil._common.bytes2human(memory_stats["swap_usage"].used),
                swap_usage_threshold,
            )
        )

    # Memory paging
    paging_stats_1 = get_paging_stats()
    time.sleep(1)
    paging_stats_2 = get_paging_stats()

    paging_in_per_sec = paging_stats_2["pages_in"] - paging_stats_1["pages_in"]
    paging_out_per_sec = paging_stats_2["pages_out"] - paging_stats_1["pages_out"]

    if paging_in_per_sec > paging_threshold or paging_out_per_sec > paging_threshold:
        warning(
            "Server is paging data. In: ({} > {}) Out: ({} > {}).".format(
                paging_in_per_sec, paging_out_per_sec, paging_threshold
            )
        )


def report_disk_performance():
    # Disk space usage
    # IOPS
    # Latency
    # Queue length
    # Avg Service time
    # Cache usage
    # Disk errors
    # Utilization %
    return


def main():
    header("CPU")
    report_server_load()
    report_cpu_usage()
    report_cpu_performance()

    header("MEMORY")
    report_memory_usage()

    header("DISK")
    report_disk_performance()

    # Network


if __name__ == "__main__":
    main()
