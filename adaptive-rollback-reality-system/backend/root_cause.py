from typing import List, Dict
import numpy as np
from .physical_state_vector import PhysicalStateVector
from .anomaly_detection import detector

def analyze_root_cause(trajectory: List[PhysicalStateVector]) -> Dict:
    """
    Analyzes the trajectory to find the earliest and most significant deviation.
    """
    if not trajectory or len(trajectory) < 2:
        return {"ranked_causes": [], "graph": []}
        
    parameters = ["air_temperature", "process_temperature", "rotational_speed", "torque", "vibration"]
    
    if not hasattr(detector, "baseline_stats") or not detector.baseline_stats:
        raise RuntimeError("Initialization Error: A verified normal baseline is required for root cause analysis.")
        
    baselines = detector.baseline_stats
        
    deviations = []
    
    for param in parameters:
        max_deviation = 0
        first_deviation_idx = -1
        max_deviation_raw = 0.0
        max_deviation_timestamp = None
        
        for i, state in enumerate(trajectory):
            val = getattr(state, param)
            
            b_std = baselines[param]["std"]
            if b_std == 0:
                b_std = 1.0 # avoid division by zero
                
            z_score = abs(val - baselines[param]["mean"]) / b_std
            
            if z_score > 3.0 and first_deviation_idx == -1: # 3 sigma rule for "significant"
                first_deviation_idx = i
                
            if z_score > max_deviation:
                max_deviation = z_score
                max_deviation_raw = abs(val - baselines[param]["mean"])
                max_deviation_timestamp = state.timestamp
                
        if max_deviation > 0:
            time_factor = (len(trajectory) - first_deviation_idx) / len(trajectory) if first_deviation_idx != -1 else 0
            contribution = (max_deviation * time_factor)
            deviations.append({
                "parameter": param,
                "baseline_value": float(baselines[param]["mean"]),
                "observed_value": float(baselines[param]["mean"] + max_deviation_raw if val >= baselines[param]["mean"] else baselines[param]["mean"] - max_deviation_raw),
                "deviation_raw": float(max_deviation_raw),
                "normalized_deviation_z": float(max_deviation),
                "timestamp": max_deviation_timestamp,
                "relative_position": float(time_factor),
                "first_deviation_index": int(first_deviation_idx),
                "contribution_score": float(contribution)
            })

    # Normalize contribution scores
    total_score = sum(d["contribution_score"] for d in deviations)
    if total_score > 0:
        for d in deviations:
            d["contribution_percent"] = float((d["contribution_score"] / total_score) * 100)
    else:
        for d in deviations:
            d["contribution_percent"] = 0.0
            
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
