from typing import List, Dict
import numpy as np
from .physical_state_vector import PhysicalStateVector

def analyze_root_cause(trajectory: List[PhysicalStateVector]) -> Dict:
    """
    Analyzes the trajectory to find the earliest and most significant deviation.
    """
    if not trajectory or len(trajectory) < 2:
        return {"ranked_causes": [], "graph": []}
        
    # Baseline is the first few states (assuming they are normal or at least the earliest)
    baseline_states = trajectory[:max(1, len(trajectory) // 4)]
    
    # Calculate baseline means and std devs
    parameters = ["air_temperature", "process_temperature", "rotational_speed", "torque", "vibration"]
    baselines = {}
    
    for param in parameters:
        values = [getattr(s, param) for s in baseline_states]
        baselines[param] = {
            "mean": np.mean(values),
            "std": np.std(values) if np.std(values) > 0 else 1.0 # avoid division by zero
        }
        
    deviations = []
    
    # Analyze the rest of the trajectory
    for param in parameters:
        max_deviation = 0
        first_deviation_idx = -1
        
        for i, state in enumerate(trajectory):
            val = getattr(state, param)
            z_score = abs(val - baselines[param]["mean"]) / baselines[param]["std"]
            
            if z_score > 3.0 and first_deviation_idx == -1: # 3 sigma rule for "significant"
                first_deviation_idx = i
                
            if z_score > max_deviation:
                max_deviation = z_score
                
        if max_deviation > 0:
            # We construct a heuristic score: 
            # High score for earlier deviation (smaller index) and higher magnitude
            time_factor = (len(trajectory) - first_deviation_idx) / len(trajectory) if first_deviation_idx != -1 else 0
            contribution = (max_deviation * time_factor)
            deviations.append({
                "parameter": param,
                "max_deviation_z": max_deviation,
                "first_deviation_index": first_deviation_idx,
                "contribution_score": contribution
            })
            
    # Normalize contribution scores
    total_score = sum(d["contribution_score"] for d in deviations)
    if total_score > 0:
        for d in deviations:
            d["contribution_percent"] = (d["contribution_score"] / total_score) * 100
    else:
        for d in deviations:
            d["contribution_percent"] = 0
            
    deviations.sort(key=lambda x: x["contribution_percent"], reverse=True)
    
    # Construct a simple causal graph representation (e.g., param1 -> param2 -> failure)
    # based on the chronological order of their first deviations
    chronological = [d for d in deviations if d["first_deviation_index"] != -1]
    chronological.sort(key=lambda x: x["first_deviation_index"])
    
    graph = [d["parameter"] for d in chronological]
    if graph:
        graph.append("Machine failure")
        
    return {
        "ranked_causes": deviations,
        "causal_graph": graph
    }
