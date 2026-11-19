"""
Tests for simulation clock respecting SIM_TIME_SCALE.
"""

import time
from datetime import datetime, timedelta, timezone

from backend.app.core.clock import SimClock


def test_clock_normal_speed():
    clk = SimClock()
    clk.reset(scale=1.0)
    t1 = clk.now()
    time.sleep(0.05)
    t2 = clk.now()
    elapsed = (t2 - t1).total_seconds()
    assert 0.04 <= elapsed <= 0.2


def test_clock_accelerated():
    clk = SimClock()
    # 60x acceleration (1 real second = 60 simulated seconds)
    clk.reset(scale=60.0)
    t1 = clk.now()
    time.sleep(0.1)
    t2 = clk.now()
    sim_elapsed = (t2 - t1).total_seconds()
    # 0.1 real seconds * 60 = 6 simulated seconds
    assert sim_elapsed >= 4.0


def test_real_seconds_until():
    clk = SimClock()
    start = datetime.now(timezone.utc)
    clk.reset(start_time=start, scale=60.0)
    future_sim_time = start + timedelta(minutes=60)  # 1 sim hour ahead
    # 1 sim hour = 60 sim minutes = 1 real minute = 60 real seconds
    real_secs = clk.real_seconds_until(future_sim_time)
    assert 55.0 <= real_secs <= 65.0
