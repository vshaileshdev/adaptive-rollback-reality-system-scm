from typing import List, Optional
from .physical_state_vector import PhysicalStateVector
from .config import settings
from .trajectory import extract_trajectory
from .root_cause import analyze_root_cause

class RingBuffer:
    def __init__(self):
        self.capacity = settings.RING_BUFFER_CAPACITY
        self.buffer: List[Optional[PhysicalStateVector]] = [None] * self.capacity
        self.head = 0
        self.is_locked = False
        self.post_failure_counter = 0
        self.failure_event = None
        self.last_extracted_trajectory = None
        self.last_root_cause = None

    def append(self, psv: PhysicalStateVector):
        if self.is_locked:
            # Continue recording for POST_FAILURE_WINDOW states, then stop completely
            if self.post_failure_counter < settings.POST_FAILURE_WINDOW:
                self.buffer[self.head] = psv
                self.head = (self.head + 1) % self.capacity
                self.post_failure_counter += 1

                # Once we gathered the post-failure states, extract trajectory
                if self.post_failure_counter == settings.POST_FAILURE_WINDOW:
                    self._extract_and_analyze()
            return

        self.buffer[self.head] = psv
        self.head = (self.head + 1) % self.capacity

    def lock(self, event_details: dict):
        if not self.is_locked:
            self.is_locked = True
            self.failure_event = event_details
            self.post_failure_counter = 0

    def unlock(self):
        self.is_locked = False
        self.failure_event = None
        self.post_failure_counter = 0

    def reset(self):
        """Cleanly resets buffer, locks, failure events, and extracted trajectories."""
        self.buffer = [None] * self.capacity
        self.head = 0
        self.is_locked = False
        self.post_failure_counter = 0
        self.failure_event = None
        self.last_extracted_trajectory = None
        self.last_root_cause = None

    def _extract_and_analyze(self):
        # Extract the ordered history from the circular buffer
        ordered_states = []
        for i in range(self.capacity):
            idx = (self.head + i) % self.capacity
            state = self.buffer[idx]
            if state is not None:
                ordered_states.append(state)

        # The trajectory extraction
        self.last_extracted_trajectory = extract_trajectory(
            ordered_states,
            settings.PRE_FAILURE_WINDOW,
            settings.POST_FAILURE_WINDOW
        )

        # Root cause analysis
        if self.last_extracted_trajectory:
            self.last_root_cause = analyze_root_cause(self.last_extracted_trajectory)

    def get_ordered_states(self) -> List[PhysicalStateVector]:
        ordered = []
        for i in range(self.capacity):
            idx = (self.head + i) % self.capacity
            state = self.buffer[idx]
            if state is not None:
                ordered.append(state)
        return ordered

ring_buffer = RingBuffer()
