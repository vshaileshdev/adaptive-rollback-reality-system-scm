# Exploratory Data Analysis (EDA) Report

## 1. Data Preprocessing
- Null values were handled.
- Non-essential string identifiers (`UDI`, `Product ID`) were dropped.
- Machine quality `Type` was numerically encoded (L=0, M=1, H=2).

## 2. Statistical Summary

### Normal Operational States
|                         |          mean |         std |    min |    max |
|:------------------------|--------------:|------------:|-------:|-------:|
| Type                    |    0.504917   |   0.673286  |    0   |    2   |
| Air temperature [K]     |  299.974      |   1.99075   |  295.3 |  304.5 |
| Process temperature [K] |  309.996      |   1.48685   |  305.7 |  313.8 |
| Rotational speed [rpm]  | 1540.26       | 167.395     | 1168   | 2695   |
| Torque [Nm]             |   39.6297     |   9.47208   |   12.6 |   70   |
| Tool wear [min]         |  106.694      |  62.9458    |    0   |  246   |
| Machine failure         |    0          |   0         |    0   |    0   |
| TWF                     |    0          |   0         |    0   |    0   |
| HDF                     |    0          |   0         |    0   |    0   |
| PWF                     |    0          |   0         |    0   |    0   |
| OSF                     |    0          |   0         |    0   |    0   |
| RNF                     |    0.00186316 |   0.0431264 |    0   |    1   |

### Failed Operational States
|                         |          mean |         std |    min |    max |
|:------------------------|--------------:|------------:|-------:|-------:|
| Type                    |    0.368732   |   0.598095  |    0   |    2   |
| Air temperature [K]     |  300.886      |   2.07147   |  295.6 |  304.4 |
| Process temperature [K] |  310.29       |   1.36369   |  306.1 |  313.7 |
| Rotational speed [rpm]  | 1496.49       | 384.944     | 1181   | 2886   |
| Torque [Nm]             |   50.1681     |  16.3745    |    3.8 |   76.6 |
| Tool wear [min]         |  143.782      |  72.7599    |    0   |  253   |
| Machine failure         |    1          |   0         |    1   |    1   |
| TWF                     |    0.135693   |   0.342969  |    0   |    1   |
| HDF                     |    0.339233   |   0.474149  |    0   |    1   |
| PWF                     |    0.280236   |   0.449778  |    0   |    1   |
| OSF                     |    0.289086   |   0.454008  |    0   |    1   |
| RNF                     |    0.00294985 |   0.0543125 |    0   |    1   |

## 3. Visualizations

### Feature Correlation Heatmap
![Correlation Heatmap](file:///C:/Users/tnith/OneDrive/Desktop/SCM/adaptive-rollback-reality-system/data/visualizations/correlation_heatmap.png)

### Torque vs Rotational Speed
![Torque vs Speed](file:///C:/Users/tnith/OneDrive/Desktop/SCM/adaptive-rollback-reality-system/data/visualizations/torque_vs_speed.png)

### Tool Wear Distribution
![Tool Wear Dist](file:///C:/Users/tnith/OneDrive/Desktop/SCM/adaptive-rollback-reality-system/data/visualizations/tool_wear_dist.png)

