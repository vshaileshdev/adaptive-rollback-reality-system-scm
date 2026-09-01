import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(SCRIPT_DIR, "../data/ai4i2020.csv")
VIS_DIR = os.path.join(SCRIPT_DIR, "../data/visualizations/")
REPORT_PATH = os.path.join(SCRIPT_DIR, "../data/EDA_Report.md")

def run_eda():
    print("Starting EDA Pipeline...")
    
    # 1. Load Dataset
    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset loaded. Shape: {df.shape}")
    
    # 2. Data Cleaning & Preprocessing
    # Handle nulls
    df.dropna(inplace=True)
    
    # Drop non-essential string IDs (UDI, Product ID)
    # We keep 'Type' as it might be useful (L, M, H) but drop string identifiers
    df_clean = df.drop(columns=["UDI", "Product ID"])
    
    # Encoding categorical 'Type'
    df_clean['Type'] = df_clean['Type'].map({'L': 0, 'M': 1, 'H': 2})
    
    print("Preprocessing complete.")
    
    # 3. Statistical Summary (Normal vs Failed)
    df_normal = df_clean[df_clean["Machine failure"] == 0]
    df_failed = df_clean[df_clean["Machine failure"] == 1]
    
    stats_normal = df_normal.describe().T[['mean', 'std', 'min', 'max']]
    stats_failed = df_failed.describe().T[['mean', 'std', 'min', 'max']]
    
    # 4. Visualizations
    os.makedirs(VIS_DIR, exist_ok=True)
    
    # Correlation Heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(df_clean.corr(), annot=True, cmap="coolwarm", fmt=".2f", linewidths=0.5)
    plt.title("Feature Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "correlation_heatmap.png"))
    plt.close()
    
    # Torque vs Speed Scatter Plot
    plt.figure(figsize=(8, 6))
    sns.scatterplot(
        data=df, 
        x="Rotational speed [rpm]", 
        y="Torque [Nm]", 
        hue="Machine failure", 
        palette={0: "green", 1: "red"},
        alpha=0.6
    )
    plt.title("Torque vs. Rotational Speed (Normal vs Failure)")
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "torque_vs_speed.png"))
    plt.close()
    
    # Tool Wear Distribution
    plt.figure(figsize=(8, 6))
    sns.histplot(data=df, x="Tool wear [min]", hue="Machine failure", multiple="stack", bins=50)
    plt.title("Tool Wear Distribution by Failure State")
    plt.tight_layout()
    plt.savefig(os.path.join(VIS_DIR, "tool_wear_dist.png"))
    plt.close()
    
    print(f"Visualizations saved to {VIS_DIR}")
    
    # 5. Generate Markdown Report
    with open(REPORT_PATH, "w") as f:
        f.write("# Exploratory Data Analysis (EDA) Report\n\n")
        f.write("## 1. Data Preprocessing\n")
        f.write("- Null values were handled.\n")
        f.write("- Non-essential string identifiers (`UDI`, `Product ID`) were dropped.\n")
        f.write("- Machine quality `Type` was numerically encoded (L=0, M=1, H=2).\n\n")
        
        f.write("## 2. Statistical Summary\n\n")
        f.write("### Normal Operational States\n")
        f.write(stats_normal.to_markdown())
        f.write("\n\n")
        
        f.write("### Failed Operational States\n")
        f.write(stats_failed.to_markdown())
        f.write("\n\n")
        
        f.write("## 3. Visualizations\n\n")
        
        f.write("### Feature Correlation Heatmap\n")
        f.write("![Correlation Heatmap](file:///" + os.path.abspath(os.path.join(VIS_DIR, "correlation_heatmap.png")).replace("\\", "/") + ")\n\n")
        
        f.write("### Torque vs Rotational Speed\n")
        f.write("![Torque vs Speed](file:///" + os.path.abspath(os.path.join(VIS_DIR, "torque_vs_speed.png")).replace("\\", "/") + ")\n\n")
        
        f.write("### Tool Wear Distribution\n")
        f.write("![Tool Wear Dist](file:///" + os.path.abspath(os.path.join(VIS_DIR, "tool_wear_dist.png")).replace("\\", "/") + ")\n\n")
        
    print(f"Report generated at {REPORT_PATH}")

if __name__ == "__main__":
    run_eda()
