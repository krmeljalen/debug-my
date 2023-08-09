#!/usr/bin/env python3
import os
import sys
import psutil
import multiprocessing

#
# Threshold settings
#

cpu_usage_threshold_pct = 80

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
    # scpufreq(current=0.649, min=500.0, max=2700.0)
    cpu_data["cpu_freq"] = psutil.cpu_freq()
    return cpu_data


# Memory helpers

#
# Report functions
#


def report_server_load():
    cpu_count = get_cpu_count()
    system_loads = get_system_load()

    for system_load in system_loads[:3]:
        if float(system_load) > cpu_count:
            warning(
                "Server load too high! ({}) which is higher than {} cpu cores available.".format(
                    ", ".join(system_loads[:3]), cpu_count
                )
            )
            return

    # Default response
    info("Server load is fine. Below {} cpu cores available.".format(cpu_count))


def report_cpu_usage():
    cpu_usage = get_cpu_usage()
    if cpu_usage > cpu_usage_threshold_pct:
        warning(
            "Server CPU usage is too high! Current cpu usage is {}% which is > {}% ".format(
                round(cpu_usage), cpu_usage_threshold_pct
            )
        )
        return

    info(
        "Server CPU usage looks fine. Current CPU usage is {}% which is < {}%.".format(
            round(cpu_usage), cpu_usage_threshold_pct
        )
    )


def report_cpu_performance():
    # IO Wait
    # Steal time
    # Context switches
    # Interrupts
    # Frequencies
    # Cache hit ratio
    return


def main():
    header("CPU")
    report_server_load()
    report_cpu_usage()
    report_cpu_performance()

    header("MEMORY")
    # Memory

    # Disk

    # Network

    # Other


if __name__ == "__main__":
    main()
