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
    storage_reduction_percent?: number;
    storage_reduction_ratio?: number;
    checkpoints_by_status?: {
        NORMAL: number;
        WARNING: number;
        CRITICAL: number;
        FAILURE: number;
    };
    effective_intervals?: {
        NORMAL: number;
        WARNING: number;
        CRITICAL: number;
    };
    target_intervals?: {
        NORMAL: number;
        WARNING: number;
        CRITICAL: number;
    };
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
export interface StorageMetrics {
    states_received: number;
    snapshots_stored: number;
    full_snapshots: number;
    delta_snapshots: number;
    skipped_states: number;
    raw_payload_bytes: number;
    stored_payload_bytes: number;
    bytes_saved: number;
    storage_reduction_percent: number;
    average_full_bytes: number;
    average_delta_bytes: number;
    average_change_score: number;
}
