from typing import List, Optional
from .physical_state_vector import PhysicalStateVector

class ReplayEngine:
    def __init__(self):
        self.trajectory: List[PhysicalStateVector] = []
        self.current_idx = 0
        self.is_playing = False
        
    def load_trajectory(self, trajectory: List[PhysicalStateVector]):
        self.trajectory = trajectory
        self.current_idx = 0
        self.is_playing = False
        
    def step_forward(self) -> Optional[PhysicalStateVector]:
        if not self.trajectory: return None
        if self.current_idx < len(self.trajectory) - 1:
            self.current_idx += 1
        return self.trajectory[self.current_idx]
        
    def step_backward(self) -> Optional[PhysicalStateVector]:
        if not self.trajectory: return None
        if self.current_idx > 0:
            self.current_idx -= 1
        return self.trajectory[self.current_idx]
        
    def get_current_state(self) -> Optional[PhysicalStateVector]:
        if not self.trajectory: return None
        return self.trajectory[self.current_idx]
        
    def reset(self):
        self.current_idx = 0
        
    def jump_to_failure(self):
        if not self.trajectory: return
        for i, state in enumerate(self.trajectory):
            if state.is_failure:
                self.current_idx = i
                return
        # default to end if no explicit failure flag
        self.current_idx = len(self.trajectory) - 1

replay_engine = ReplayEngine()
