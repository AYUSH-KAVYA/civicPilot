"""
CivicPilot Simulation Clock
Honours SIM_TIME_SCALE so multi-hour/multi-day SLAs play out in minutes during demos and tests.
ALL deadline math across the multi-agent system uses clock.now().
"""

from datetime import datetime, timezone
from typing import Optional

from backend.app.core.config import get_settings


class SimClock:
    def __init__(self) -> None:
        self._real_start: datetime = datetime.now(timezone.utc)
        self._sim_start: datetime = self._real_start
        self._custom_scale: Optional[float] = None

    def reset(self, start_time: Optional[datetime] = None, scale: Optional[float] = None) -> None:
        """Reset the simulation clock anchor point and optional scale override."""
        self._real_start = datetime.now(timezone.utc)
        self._sim_start = start_time or self._real_start
        self._custom_scale = scale

    @property
    def scale(self) -> float:
        if self._custom_scale is not None:
            return self._custom_scale
        return get_settings().SIM_TIME_SCALE

    def now(self) -> datetime:
        """Return the current simulated time in UTC."""
        scale = self.scale
        real_now = datetime.now(timezone.utc)
        if scale <= 0 or abs(scale - 1.0) < 1e-6:
            return real_now

        real_elapsed = real_now - self._real_start
        sim_elapsed = real_elapsed * scale
        return self._sim_start + sim_elapsed

    def real_seconds_until(self, target_sim_time: datetime) -> float:
        """
        Convert a future simulated deadline into real seconds to wait (for timers/sleep).
        """
        scale = self.scale
        current_sim = self.now()
        sim_delta = (target_sim_time - current_sim).total_seconds()
        if sim_delta <= 0:
            return 0.0
        if scale <= 0:
            return sim_delta
        return sim_delta / scale


# Global clock instance
clock = SimClock()


def now() -> datetime:
    """Convenience function returning clock.now() in UTC."""
    return clock.now()
