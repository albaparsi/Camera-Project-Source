"""Filter wheel control backed by the stepper motor helpers."""

from __future__ import annotations

from hardware.move_motor import POSITIONS_PER_REV, move_filters


class StepperFilterWheel:
    """Move filter IDs (0..7) across a 9-position wheel with a reference slot."""

    def __init__(
        self,
        *,
        start_position: int = 0,
        position_count: int = POSITIONS_PER_REV,
        filter_count: int = 8,
        first_filter_position: int = 1,
    ):
        if position_count <= 0:
            raise ValueError("position_count must be > 0")
        if filter_count <= 0:
            raise ValueError("filter_count must be > 0")
        if filter_count >= position_count:
            raise ValueError("filter_count must be less than position_count")

        self.position_count = int(position_count)
        self.filter_count = int(filter_count)
        self.first_filter_position = int(first_filter_position) % self.position_count
        self.current_position = int(start_position) % self.position_count

    def _position_for_filter_id(self, filter_id: int) -> int:
        filter_idx = int(filter_id)
        if filter_idx < 0 or filter_idx >= self.filter_count:
            raise ValueError(
                f"filter_id must be in range 0..{self.filter_count - 1}; got {filter_id}"
            )

        return (self.first_filter_position + filter_idx) % self.position_count

    def move_to(self, filter_id: int) -> None:
        """Move from current wheel position to the requested filter."""

        target_position = self._position_for_filter_id(filter_id)
        delta = (target_position - self.current_position) % self.position_count

        if delta > 0:
            move_filters(delta)

        self.current_position = target_position