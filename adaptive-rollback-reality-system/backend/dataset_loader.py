import pandas as pd
import numpy as np
import os

DATASET_PATH = "data/ai4i2020.csv"

class DatasetLoader:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dataset_path = os.path.join(self.base_path, DATASET_PATH)
        
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError("AI4I dataset not found! Please ensure data/ai4i2020.csv exists.")
            
        self.df = pd.read_csv(self.dataset_path)
        
        # Sort by normal then failed so we stream normal data before hitting failure for demo purposes
        # Or just shuffle the normal data and append some failed data at the end
        normal_df = self.df[self.df["Machine failure"] == 0].sample(frac=1).reset_index(drop=True)
        failed_df = self.df[self.df["Machine failure"] == 1].sample(frac=1).reset_index(drop=True)
        
        # Create a demo sequence: 200 normal points followed by 1 failed point
        self.demo_df = pd.concat([normal_df.head(200), failed_df.head(1)], ignore_index=True)
        self.current_idx = 0
        
    def get_next_state(self) -> dict:
        if self.current_idx >= len(self.demo_df):
            self.current_idx = 0 # loop
            
        row = self.demo_df.iloc[self.current_idx]
        self.current_idx += 1
        
        # Determine failure cause for the causal graph
        fail_causes = []
        if row["TWF"] == 1: fail_causes.append("TWF")
        if row["HDF"] == 1: fail_causes.append("HDF")
        if row["PWF"] == 1: fail_causes.append("PWF")
        if row["OSF"] == 1: fail_causes.append("OSF")
        
        # We synthesize vibration and current slightly as they are not in AI4I directly,
        # but are needed for the multi-modal PSV definition we made.
        # Alternatively, we just map what we have.
        
        return {
            "air_temperature": float(row["Air temperature [K]"]),
            "process_temperature": float(row["Process temperature [K]"]),
            "rotational_speed": float(row["Rotational speed [rpm]"]),
            "torque": float(row["Torque [Nm]"]),
            "tool_wear": float(row["Tool wear [min]"]),
            "vibration": float(np.random.normal(0.1, 0.02)), # mock for PSV completeness
            "current": float(np.random.normal(1.0, 0.1)), # mock for PSV completeness
            "is_failure": bool(row["Machine failure"] == 1),
            "_true_causes": fail_causes # passing this purely for demo validation if needed
        }
    
    def reset(self):
        self.current_idx = 0

dataset_loader = DatasetLoader()
