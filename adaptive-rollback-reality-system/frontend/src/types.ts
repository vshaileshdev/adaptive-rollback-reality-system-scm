export interface PhysicalStateVector {
    timestamp: string;
    device_id: string;
    air_temperature: number;
    process_temperature: number;
    humidity: number;
    vibration: number;
    rotational_speed: number;
    torque: number;
    current: number;
    tool_wear: number;
    anomaly_score: number;
    checkpoint_level: "NORMAL" | "WARNING" | "CRITICAL";
    machine_status: "NORMAL" | "WARNING" | "CRITICAL" | "FAILURE";
    is_failure: boolean;
}

export interface Metrics {
    total_states_received: number;
    total_checkpoints: number;
    storage_saved: number;
}

export interface RootCause {
    ranked_causes: {
        parameter: string;
        max_deviation_z: number;
        first_deviation_index: number;
        contribution_score: number;
        contribution_percent: number;
    }[];
    causal_graph: string[];
}
export const _dummy = 1;
