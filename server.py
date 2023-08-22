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


def warning(msg, suggestion=None):
    print("[WARN] {}".format(msg))
    if suggestion:
        print("Suggestion:", suggestion)


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


def report_cpu_performance():
    # Load
    cpu_count = get_cpu_count()
    system_loads = get_system_load()

    high_system_load = False
    for system_load in system_loads[:3]:
        if float(system_load) > cpu_count:
            high_system_load = True

    if high_system_load:
        suggestion = (
            "Upscale server or check which processes are taking most CPU or I/O time."
        )
        warning(
            f"Server load too high! ({', '.join(system_loads[:3])} > {cpu_count})",
            suggestion,
        )
    else:
        info(f"Load is OK. ({system_load} < {cpu_count} CPU cores)")

    # CPU usage
    cpu_usage = get_cpu_usage()

    if cpu_usage > cpu_usage_threshold_pct:
        suggestion = "Upscale server or check which processes are taking most CPU time."
        warning(
            f"CPU usage is too high! ({round(cpu_usage)}% > {cpu_usage_threshold_pct}%)",
            suggestion,
        )
    else:
        info(f"CPU usage is OK. ({round(cpu_usage)}% < {cpu_usage_threshold_pct}%)")

    cpu_performance_stats = get_cpu_performance()

    # IO Wait
    if cpu_performance_stats["cpu_times"].iowait > cpu_iowait_threshold_pct:
        suggestion = (
            "There are processes doing a lot of disk or network operations. "
            "Check disk and network metrics to determine the cause."
        )
        warning(
            f"IO wait is high! "
            f"({cpu_performance_stats['cpu_times'].iowait}% > {cpu_iowait_threshold_pct}%) "
            f"This means there are CPU-waiting disk or network operations.",
            suggestion,
        )
    else:
        info(f"IO wait is OK. ({cpu_performance_stats['cpu_times'].iowait}% < {cpu_iowait_threshold_pct}%)")

    # Steal time
    if cpu_performance_stats["cpu_times"].steal > cpu_steal_threshold_pct:
        suggestion = "Other VMs on this host are affecting this server's CPU resources. Consider moving the VM to another host that is not overloaded."
        warning(
            f"CPU Steal time detected! "
            f"({cpu_performance_stats['cpu_times'].steal}% > {cpu_steal_threshold_pct}%) ",
            suggestion
        )
    else:
        info(f"CPU Steal time is OK. ({cpu_performance_stats['cpu_times'].steal}% < {cpu_steal_threshold_pct}%)")

    cpu_stats_1 = get_cpu_performance()
    time.sleep(1)
    cpu_stats_2 = get_cpu_performance()

    # Context switches
    ctx_switches_per_second = (
        cpu_stats_2["cpu_stats"].ctx_switches - cpu_stats_1["cpu_stats"].ctx_switches
    )
    if ctx_switches_per_second > cpu_ctx_switches_threshold:
        suggestion = "Consider pinning processes to specific cores or optimizing application logic."
        warning(
            f"CPU is experiencing a high number of context switches. "
            f"({ctx_switches_per_second}/s > {cpu_ctx_switches_threshold}/s) ",
            suggestion,
        )
    else:
        info(f"Context switching is OK. ({ctx_switches_per_second}/s < {cpu_ctx_switches_threshold}/s)")

    # Interrupts
    interrupts_per_second = (
        cpu_stats_2["cpu_stats"].interrupts - cpu_stats_1["cpu_stats"].interrupts
    )
    if interrupts_per_second > cpu_interrupts_threshold:
        warning(
            f"CPU is frequently interrupted by hardware events. "
            f"({interrupts_per_second}/s > {cpu_interrupts_threshold}/s)"
        )
    else:
        info(f"CPU interrupts are OK. ({interrupts_per_second}/s < {cpu_interrupts_threshold}/s)")

    return


def report_memory_performance():
    memory_stats = get_memory_stats()

    # Memory
    available_memory = memory_stats["memory_usage"].available
    total_memory = memory_stats["memory_usage"].total
    available_mem_pct = round(available_memory / total_memory * 100)

    if available_mem_pct < memory_available_threshold:
        suggestion = "Lower the memory or add more memory to the server."
        warning(
            f"Available memory is low! ({available_mem_pct}% < {memory_available_threshold}%)",
            suggestion
        )
    else:
        info(f"Memory usage is OK. ({available_mem_pct}% > {memory_available_threshold}%)")

    # Swap
    swap_used = memory_stats["swap_usage"].used
    if swap_used > swap_usage_threshold:
        suggestion = "Consider adding more memory to the server."
        warning(
            f"Server was swapping at one point. ({psutil._common.bytes2human(swap_used)} > {swap_usage_threshold})",
            suggestion
        )
    else:
        info(f"Swap usage is OK. ({psutil._common.bytes2human(swap_used)} < {psutil._common.bytes2human(swap_usage_threshold)})")

    # Paging
    paging_stats_1 = get_paging_stats()
    time.sleep(1)
    paging_stats_2 = get_paging_stats()

    paging_in_per_sec = paging_stats_2["pages_in"] - paging_stats_1["pages_in"]
    paging_out_per_sec = paging_stats_2["pages_out"] - paging_stats_1["pages_out"]

    if paging_in_per_sec > paging_threshold or paging_out_per_sec > paging_threshold:
        warning(
            f"Server is paging data. In: ({paging_in_per_sec} > {paging_threshold}) Out: ({paging_out_per_sec} > {paging_threshold})"
        )
    else:
        info(f"Memory paging is OK. In: ({paging_in_per_sec} < {paging_threshold}) Out: ({paging_out_per_sec} < {paging_threshold})")


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
    report_cpu_performance()

    header("MEMORY")
    report_memory_performance()

    header("DISK")
    report_disk_performance()

    # Network


if __name__ == "__main__":
    main()
