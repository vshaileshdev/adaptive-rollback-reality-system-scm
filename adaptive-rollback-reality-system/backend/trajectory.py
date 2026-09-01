from typing import List
from .physical_state_vector import PhysicalStateVector

def extract_trajectory(
    ordered_states: List[PhysicalStateVector],
    pre_window: int,
    post_window: int
) -> List[PhysicalStateVector]:
    """
    Finds the failure state in the ordered_states and extracts the window around it.
    """
    failure_idx = -1
    for i, state in enumerate(ordered_states):
        if state.is_failure:
            failure_idx = i
            break
            
    if failure_idx == -1:
        # If no explicit failure state, assume the last one is the failure
        failure_idx = len(ordered_states) - 1 - post_window
        
    start_idx = max(0, failure_idx - pre_window)
    end_idx = min(len(ordered_states), failure_idx + post_window + 1)
    
    return ordered_states[start_idx:end_idx]
