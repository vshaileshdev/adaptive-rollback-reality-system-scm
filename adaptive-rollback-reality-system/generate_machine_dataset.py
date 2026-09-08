#!/usr/bin/env python3
"""
Synthetic Industrial Machine Telemetry Generator
Project: Adaptive Rollback Reality System for IoT Machines
Description: Generates continuous, stateful time-series sensor telemetry 
             simulating industrial machines progressing through degradation 
             phases to failure events.
"""

import os
import json
import math
import datetime
import numpy as np
import pandas as pd

# Optional Matplotlib for diagnostic visualization
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# =====================================================================
# CONFIGURATION PARAMETERS (Adjustable)
# =====================================================================
CONFIG = {
    "NUM_MACHINES": 5,
    "OBSERVATIONS_PER_MACHINE": 2000,
    "SAMPLING_INTERVAL_SECONDS": 2,
    "RANDOM_SEED": 42,
    "OUTPUT_DIR": "data",
    "VISUALIZATION_DIR": "visualizations",
    "GENERATE_PLOTS": True,
    
    # Phase boundaries as percentage of failure timeline (0.0 to 1.0)
    "PHASE_THRESHOLDS": {
        "NORMAL_END": 0.65,            # 0% to 65% of timeline
        "EARLY_DEGRADATION_END": 0.82, # 65% to 82%
        "WARNING_END": 0.92,           # 82% to 92%
        "CRITICAL_END": 0.985,         # 92% to 98.5%
        # FAILURE occurs at 98.5% to 98.6%
        # POST_FAILURE is remaining timeline up to 100%
    },

    # Electrical parameters (3-Phase Industrial Motor Assumptions)
    "ELECTRICAL": {
        "NOMINAL_VOLTAGE_V": 400.0,
        "POWER_FACTOR": 0.85,
        "BASE_EFFICIENCY": 0.90
    }
}

# Failure mechanism mapping per machine
FAILURE_TYPE_MAP = {
    1: "TYPE_A_THERMAL",
    2: "TYPE_B_VIBRATION",
    3: "TYPE_C_MECHANICAL_OVERLOAD",
    4: "TYPE_D_TOOL_WEAR",
    5: "TYPE_E_SUDDEN_FAILURE"
}


# =====================================================================
# SIMULATOR CLASS
# =====================================================================
class MachineSimulator:
    def __init__(self, machine_index: int, config: dict):
        self.config = config
        self.machine_id = f"MACHINE_{str(machine_index).zfill(3)}"
        self.failure_type = FAILURE_TYPE_MAP.get(machine_index, "TYPE_A_THERMAL")
        self.num_obs = config["OBSERVATIONS_PER_MACHINE"]
        self.interval_sec = config["SAMPLING_INTERVAL_SECONDS"]
        
        # Randomized failure point between 92% and 97% of machine sequence length
        np.random.seed(config["RANDOM_SEED"] + machine_index * 100)
        fail_pct = np.random.uniform(0.92, 0.97)
        self.failure_idx = int(self.num_obs * fail_pct)
        self.failure_event_id = f"{self.machine_id}_F001"

        # Unique physical baseline per machine
        self.base_air_temp = np.random.uniform(20.0, 25.0)
        self.base_process_temp = self.base_air_temp + np.random.uniform(18.0, 22.0)
        self.base_humidity = np.random.uniform(40.0, 50.0)
        self.base_vibration = np.random.uniform(0.10, 0.14)  # mm/s RMS
        self.base_rpm = np.random.uniform(1480.0, 1520.0)
        self.base_torque = np.random.uniform(38.0, 42.0)      # Nm
        self.tool_wear_rate = np.random.uniform(0.08, 0.12)  # minutes wear per operating minute

        # Autocorrelation memory factor (alpha): high alpha = strong continuity
        self.alpha = 0.92

    def _get_phase(self, idx: int) -> str:
        """Determines lifecycle phase based on position relative to failure index."""
        if idx > self.failure_idx:
            return "POST_FAILURE"
        elif idx == self.failure_idx:
            return "FAILURE"
            
        ratio = idx / self.failure_idx
        p = self.config["PHASE_THRESHOLDS"]
        
        if ratio < p["NORMAL_END"]:
            return "NORMAL"
        elif ratio < p["EARLY_DEGRADATION_END"]:
            return "EARLY_DEGRADATION"
        elif ratio < p["WARNING_END"]:
            return "WARNING"
        else:
            return "CRITICAL"

    def _get_degradation_stage(self, phase: str) -> int:
        stage_map = {
            "NORMAL": 0,
            "EARLY_DEGRADATION": 1,
            "WARNING": 2,
            "CRITICAL": 3,
            "FAILURE": 4,
            "POST_FAILURE": 5
        }
        return stage_map[phase]

    def generate(self) -> tuple[list, dict]:
        records = []
        start_time = datetime.datetime(2026, 1, 1, 8, 0, 0)
        
        # State tracking variables
        air_temp = self.base_air_temp
        process_temp = self.base_process_temp
        humidity = self.base_humidity
        vibration = self.base_vibration
        rpm = self.base_rpm
        torque = self.base_torque
        tool_wear = 0.0

        for idx in range(self.num_obs):
            timestamp = start_time + datetime.timedelta(seconds=idx * self.interval_sec)
            elapsed_sec = idx * self.interval_sec
            phase = self._get_phase(idx)
            deg_stage = self._get_degradation_stage(phase)

            # Time To Failure (TTF) Calculation
            if idx <= self.failure_idx:
                ttf_sec = (self.failure_idx - idx) * self.interval_sec
            else:
                ttf_sec = None  # Null post-failure

            # Normalized degradation intensity (0.0 during NORMAL up to 1.0 at FAILURE)
            if phase == "NORMAL":
                deg_intensity = 0.0
            elif phase in ["EARLY_DEGRADATION", "WARNING", "CRITICAL"]:
                norm_idx = idx - (self.failure_idx * self.config["PHASE_THRESHOLDS"]["NORMAL_END"])
                denom = self.failure_idx - (self.failure_idx * self.config["PHASE_THRESHOLDS"]["NORMAL_END"])
                deg_intensity = max(0.0, min(1.0, norm_idx / max(1, denom)))
            elif phase == "FAILURE":
                deg_intensity = 1.0
            else:
                deg_intensity = 0.0  # Post-failure handoff

            # =========================================================
            # PHYSICAL STATE VECTOR EVOLUTION (Stateful AR(1) + Drift)
            # =========================================================
            if phase != "POST_FAILURE":
                # Continuous baseline wear accumulation
                tool_wear += (self.interval_sec / 60.0) * self.tool_wear_rate

                # Targets init
                target_air_temp = self.base_air_temp + np.random.normal(0, 0.1)
                target_process_temp = target_air_temp + 20.0
                target_humidity = self.base_humidity + np.random.normal(0, 0.2)
                target_vibration = self.base_vibration
                target_rpm = self.base_rpm
                target_torque = self.base_torque

                # Inject failure-specific physics drifts
                if self.failure_type == "TYPE_A_THERMAL":
                    target_process_temp += 35.0 * (deg_intensity ** 1.8)
                    target_vibration += 0.3 * deg_intensity
                    
                elif self.failure_type == "TYPE_B_VIBRATION":
                    target_vibration += 4.5 * (deg_intensity ** 2.2)
                    target_torque += 6.0 * deg_intensity * np.random.uniform(-0.5, 1.5)
                    target_rpm += np.random.normal(0, 8.0 * deg_intensity)

                elif self.failure_type == "TYPE_C_MECHANICAL_OVERLOAD":
                    target_torque += 45.0 * (deg_intensity ** 1.5)
                    target_rpm -= 180.0 * (deg_intensity ** 1.2)
                    target_vibration += 0.8 * deg_intensity
                    target_process_temp += 15.0 * deg_intensity

                elif self.failure_type == "TYPE_D_TOOL_WEAR":
                    tool_wear_accel = 0.4 * (deg_intensity ** 2)
                    tool_wear += tool_wear_accel
                    target_torque += 15.0 * (tool_wear / 100.0)
                    target_vibration += 1.2 * (tool_wear / 100.0)
                    target_process_temp += 10.0 * (tool_wear / 100.0)

                elif self.failure_type == "TYPE_E_SUDDEN_FAILURE":
                    # Sudden failure stays near nominal until CRITICAL stage
                    if phase == "CRITICAL":
                        crit_progress = (idx - (self.failure_idx * 0.92)) / max(1, (self.failure_idx * 0.08))
                        target_vibration += 5.0 * (crit_progress ** 3)
                        target_torque += 35.0 * (crit_progress ** 3)
                        target_rpm -= 200.0 * (crit_progress ** 3)

                # AR(1) Stateful Smoothing (new_val = alpha * old_val + (1 - alpha) * target + noise)
                air_temp = self.alpha * air_temp + (1 - self.alpha) * target_air_temp + np.random.normal(0, 0.03)
                humidity = np.clip(self.alpha * humidity + (1 - self.alpha) * target_humidity + np.random.normal(0, 0.05), 20.0, 80.0)
                process_temp = self.alpha * process_temp + (1 - self.alpha) * target_process_temp + np.random.normal(0, 0.08)
                vibration = max(0.01, self.alpha * vibration + (1 - self.alpha) * target_vibration + np.random.normal(0, 0.005))
                rpm = max(0.0, self.alpha * rpm + (1 - self.alpha) * target_rpm + np.random.normal(0, 0.8))
                torque = max(0.0, self.alpha * torque + (1 - self.alpha) * target_torque + np.random.normal(0, 0.15))

                # Physical Coupling: Mechanical Power & Current Calculation
                angular_velocity = (rpm * 2.0 * math.pi) / 60.0  # rad/s
                mech_power_w = torque * angular_velocity           # Watts
                
                v_line = self.config["ELECTRICAL"]["NOMINAL_VOLTAGE_V"]
                pf = self.config["ELECTRICAL"]["POWER_FACTOR"]
                eff = self.config["ELECTRICAL"]["BASE_EFFICIENCY"] - (0.05 * deg_intensity) # Efficiency degrades
                
                elec_current_a = mech_power_w / (math.sqrt(3) * v_line * pf * eff)
                elec_power_w = math.sqrt(3) * v_line * elec_current_a * pf

            else:
                # POST_FAILURE: Machine trip / Shutdown state
                rpm = max(0.0, rpm * 0.70)             # Rapid spin-down
                torque = 0.0
                mech_power_w = 0.0
                elec_current_a = 0.10                   # Minimal standby current
                elec_power_w = 0.0
                vibration = max(0.01, vibration * 0.85) # Vibrations settle to ambient
                # Process temperature cools down towards ambient air temperature
                process_temp = air_temp + (process_temp - air_temp) * 0.98

            # Reference synthetic ground-truth metrics (NOT for model input features)
            health_score = max(0.0, min(100.0, 100.0 - (deg_intensity * 95.0) + np.random.normal(0, 1.0)))
            anomaly_score = max(0.0, min(1.0, (deg_intensity ** 1.5) + np.random.normal(0, 0.02)))
            if phase == "FAILURE":
                health_score = 0.0
                anomaly_score = 1.0

            # Record dict
            row = {
                # Identification
                "machine_id": self.machine_id,
                "sequence_id": idx,
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_time_seconds": elapsed_sec,
                
                # Sensor Telemetry (Input Features)
                "air_temperature": round(air_temp, 2),
                "process_temperature": round(process_temp, 2),
                "humidity": round(humidity, 2),
                "vibration": round(vibration, 4),
                "rotational_speed": round(rpm, 1),
                "torque": round(torque, 2),
                "tool_wear": round(tool_wear, 2),
                "current": round(elec_current_a, 2),
                "power": round(elec_power_w, 2),

                # Ground-Truth / Reference Labels (Targets only)
                "machine_status": phase,
                "degradation_stage": deg_stage,
                "synthetic_health_score": round(health_score, 1),
                "synthetic_anomaly_score": round(anomaly_score, 4),
                "failure_flag": 1 if phase == "FAILURE" else 0,
                "failure_type": self.failure_type,
                "failure_event_id": self.failure_event_id if phase in ["FAILURE", "POST_FAILURE"] else "",
                "time_to_failure_seconds": ttf_sec if ttf_sec is not None else "",
                "failure_within_30s": 1 if (ttf_sec is not None and 0 <= ttf_sec <= 30) else 0,
                "failure_within_60s": 1 if (ttf_sec is not None and 0 <= ttf_sec <= 60) else 0
            }
            records.append(row)

        event_summary = {
            "machine_id": self.machine_id,
            "failure_type": self.failure_type,
            "failure_event_id": self.failure_event_id,
            "failure_sequence_id": self.failure_idx,
            "failure_timestamp": (start_time + datetime.timedelta(seconds=self.failure_idx * self.interval_sec)).strftime("%Y-%m-%d %H:%M:%S"),
            "pre_failure_duration_seconds": self.failure_idx * self.interval_sec
        }

        return records, event_summary


# =====================================================================
# GENERATION, VALIDATION & EXPORT SUITE
# =====================================================================
def run_generator():
    print("=" * 70)
    print("STARTING INDUSTRIAL MACHINE TELEMETRY GENERATOR")
    print("=" * 70)

    os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)
    os.makedirs(CONFIG["VISUALIZATION_DIR"], exist_ok=True)

    all_telemetry = []
    failure_events = []

    for i in range(1, CONFIG["NUM_MACHINES"] + 1):
        sim = MachineSimulator(machine_index=i, config=CONFIG)
        records, summary = sim.generate()
        all_telemetry.extend(records)
        failure_events.append(summary)
        print(f" Generated {len(records)} observations for {sim.machine_id} [{sim.failure_type}]")

    df_telemetry = pd.DataFrame(all_telemetry)
    df_events = pd.DataFrame(failure_events)

    # File exports
    telemetry_path = os.path.join(CONFIG["OUTPUT_DIR"], "machine_timeseries.csv")
    events_path = os.path.join(CONFIG["OUTPUT_DIR"], "failure_events.csv")
    metadata_path = os.path.join(CONFIG["OUTPUT_DIR"], "dataset_metadata.json")

    df_telemetry.to_csv(telemetry_path, index=False)
    df_events.to_csv(events_path, index=False)

    metadata = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "random_seed": CONFIG["RANDOM_SEED"],
        "num_machines": CONFIG["NUM_MACHINES"],
        "total_observations": len(df_telemetry),
        "sampling_interval_seconds": CONFIG["SAMPLING_INTERVAL_SECONDS"],
        "disclaimer": "Synthetic physically-inspired temporal machine telemetry for digital-twin simulation and adaptive rollback experimentation.",
        "sensor_units": {
            "air_temperature": "°C",
            "process_temperature": "°C",
            "humidity": "%",
            "vibration": "mm/s RMS",
            "rotational_speed": "RPM",
            "torque": "Nm",
            "tool_wear": "minutes",
            "current": "Amperes",
            "power": "Watts"
        }
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\nExports completed:")
    print(f" - Telemetry Data: {telemetry_path}")
    print(f" - Failure Events: {events_path}")
    print(f" - Metadata JSON:  {metadata_path}")

    # =====================================================================
    # AUTOMATED VALIDATION SUITE
    # =====================================================================
    print("\n" + "=" * 70)
    print("RUNNING AUTOMATED VALIDATION SUITE")
    print("=" * 70)

    val_errors = []

    # 1. Row count validation
    expected_rows = CONFIG["NUM_MACHINES"] * CONFIG["OBSERVATIONS_PER_MACHINE"]
    if len(df_telemetry) != expected_rows:
        val_errors.append(f"Row count mismatch! Expected {expected_rows}, got {len(df_telemetry)}")

    # 2. Per-machine validation checks
    for m_id, group in df_telemetry.groupby("machine_id"):
        # Chronological & Sequence ID ordering
        if not group["sequence_id"].is_monotonic_increasing:
            val_errors.append(f"[{m_id}] sequence_id is not strictly increasing!")
            
        timestamps = pd.to_datetime(group["timestamp"])
        if not timestamps.is_monotonic_increasing:
            val_errors.append(f"[{m_id}] timestamps are not strictly chronological!")
            
        if group["timestamp"].duplicated().any():
            val_errors.append(f"[{m_id}] contains duplicate timestamps!")

        # Physical boundary checks
        if (group["rotational_speed"] < 0).any():
            val_errors.append(f"[{m_id}] contains negative RPM!")
        if (group["torque"] < 0).any():
            val_errors.append(f"[{m_id}] contains negative Torque!")
        if (group["vibration"] < 0).any():
            val_errors.append(f"[{m_id}] contains negative Vibration!")
        if (group["current"] < 0).any():
            val_errors.append(f"[{m_id}] contains negative Current!")
        if (group["tool_wear"] < 0).any():
            val_errors.append(f"[{m_id}] contains negative Tool Wear!")

        # Tool wear monotonicity during active phases
        active_mask = group["machine_status"] != "POST_FAILURE"
        active_wear = group.loc[active_mask, "tool_wear"]
        if not active_wear.is_monotonic_increasing:
            val_errors.append(f"[{m_id}] tool_wear decreases during active operation!")

        # Failure flag & TTF reach zero check
        fail_rows = group[group["failure_flag"] == 1]
        if len(fail_rows) != 1:
            val_errors.append(f"[{m_id}] Expected exactly 1 failure event row, found {len(fail_rows)}")
        else:
            if fail_rows["time_to_failure_seconds"].values[0] != 0:
                val_errors.append(f"[{m_id}] time_to_failure_seconds is not 0 at failure event!")

    if val_errors:
        print(" VALIDATION FAILED with errors:")
        for err in val_errors:
            print(f"   - {err}")
    else:
        print(" ALL STRUCTURAL & PHYSICAL VALIDATIONS PASSED PERFECTLY!")

    # =====================================================================
    # TEMPORAL QUALITY DIAGNOSTIC (Lag-1 Autocorrelation)
    # =====================================================================
    print("\n" + "=" * 70)
    print("TEMPORAL CONTINUITY DIAGNOSTIC (Lag-1 Autocorrelation)")
    print("=" * 70)
    print("A high Lag-1 autocorrelation (> 0.85) proves smooth stateful continuity.")
    
    m1_group = df_telemetry[df_telemetry["machine_id"] == "MACHINE_001"]
    sensors = ["process_temperature", "vibration", "rotational_speed", "torque", "current"]
    
    for s in sensors:
        r1 = m1_group[s].autocorr(lag=1)
        print(f" - {s:<22} Lag-1 Pearson r = {r1:.4f}")

    # =====================================================================
    # DIAGNOSTIC PLOTTING (Optional)
    # =====================================================================
    if CONFIG["GENERATE_PLOTS"] and HAS_MATPLOTLIB:
        print("\n" + "=" * 70)
        print("GENERATING DIAGNOSTIC TELEMETRY PLOTS")
        print("=" * 70)
        
        plot_machine = "MACHINE_001"
        pm_data = df_telemetry[df_telemetry["machine_id"] == plot_machine]
        fail_idx = pm_data[pm_data["failure_flag"] == 1]["sequence_id"].values[0]
        
        fig, axes = plt.subplots(5, 1, figsize=(12, 10), sharex=True)
        
        axes[0].plot(pm_data["sequence_id"], pm_data["process_temperature"], color="tab:red")
        axes[0].set_ylabel("Process Temp (°C)")
        
        axes[1].plot(pm_data["sequence_id"], pm_data["vibration"], color="tab:orange")
        axes[1].set_ylabel("Vibration (mm/s)")
        
        axes[2].plot(pm_data["sequence_id"], pm_data["torque"], color="tab:green")
        axes[2].set_ylabel("Torque (Nm)")
        
        axes[3].plot(pm_data["sequence_id"], pm_data["rotational_speed"], color="tab:blue")
        axes[3].set_ylabel("Speed (RPM)")
        
        axes[4].plot(pm_data["sequence_id"], pm_data["current"], color="tab:purple")
        axes[4].set_ylabel("Current (A)")
        axes[4].set_xlabel("Sequence ID (Observations)")

        for ax in axes:
            ax.axvline(x=fail_idx, color="black", linestyle="--", alpha=0.8, label="Failure Event")
            ax.grid(True, linestyle=":", alpha=0.6)

        axes[0].set_title(f"Continuous Telemetry & Failure Progression — {plot_machine} [{FAILURE_TYPE_MAP[1]}]")
        plt.tight_layout()
        plot_path = os.path.join(CONFIG["VISUALIZATION_DIR"], f"{plot_machine}_telemetry.png")
        plt.savefig(plot_path, dpi=150)
        plt.close()
        print(f" Diagnostic plot saved to: {plot_path}")

    print("\n" + "=" * 70)
    print("DATASET GENERATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_generator()