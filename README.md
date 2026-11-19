# RouteOpt: Last-Mile Delivery Route Optimization & Fleet Planning

[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B.svg)](https://streamlit.io)
[![OR--Tools](https://img.shields.io/badge/Google-OR--Tools-orange.svg)](https://developers.google.com/optimization)

**RouteOpt** is a high-performance last-mile delivery route optimization and fleet planning system. It pairs classic combinatorial heuristics with modern metaheuristics (Google OR-Tools) and exact mathematical programming (MILP via HiGHS/SciPy), backed by an interactive, modern Streamlit operations dashboard.

---

## 📑 Table of Contents
- [1. Project Overview](#-1-project-overview)
- [2. System Architecture](#-2-system-architecture)
- [3. Key Features](#-3-key-features)
- [4. Technologies & Frameworks](#-4-technologies--frameworks)
- [5. Prerequisites](#-5-prerequisites)
- [6. Installation & Environment Setup](#-6-installation--environment-setup)
- [7. How to Run the Project](#-7-how-to-run-the-project)
- [8. Complete End-to-End User Guide](#-8-complete-end-to-end-user-guide)
- [9. Benchmark Datasets & Sample Data](#-9-benchmark-datasets--sample-data)
- [10. Command Line Interface (CLI)](#-10-command-line-interface-cli)
- [11. Testing & Validation](#-11-testing--validation)
- [12. Troubleshooting Guide](#-12-troubleshooting-guide)
- [13. License](#-13-license)

---

## 🌟 1. Project Overview

Last-mile logistics accounts for over **50% of total shipping costs**. RouteOpt solves the classic **Capacitated Vehicle Routing Problem (CVRP)** and **Vehicle Routing Problem with Time Windows (VRPTW)**, enabling logistics planners and researchers to:
- Minimize overall fleet travel distance and operational hours.
- Reduce active vehicle requirements via lexicographic optimization.
- Adhere strictly to payload capacities, driver delivery time windows, and shift limits.
- Visualize circuit itineraries on interactive geographic maps.
- Execute Monte Carlo sensitivity tests and benchmark comparisons against world-record Best Known Solutions (BKS).

---

## 🏗️ 2. System Architecture

```text
ROUTEOPT/
├── app/                              # Modern Streamlit Dashboard
│   ├── Home.py                       # Main console overview & quick actions
│   ├── ui_theme.py                   # Unified modern UI design system
│   └── pages/                        # Specialized workflow modules
│       ├── 1_Delivery_Data.py        # Ingestion, schema audit, sample loader
│       ├── 2_Route_Optimization.py   # Solver selection, hyperparameter tuning
│       ├── 3_Route_Map.py            # Plotly interactive stop cartography
│       ├── 4_Model_Comparison.py     # Side-by-side solver benchmarking
│       └── 5_Scenario_Analysis.py    # Monte Carlo sensitivity stress testing
├── src/routeopt/                     # Core Mathematical & Engineering Library
│   ├── algorithms/                   # Heuristics (Nearest Neighbor, Savings, 2-Opt)
│   ├── data/                         # Loaders (CSV, CVRPLIB, Solomon) & Schema
│   ├── evaluation/                   # Independent Validator, BKS Gap, Metrics
│   ├── geo/                          # Euclidean, Haversine, OSRM Matrix Engine
│   ├── optimization/                 # Google OR-Tools CVRP/VRPTW & HiGHS MILP
│   ├── prediction/                   # Travel time & ETA estimation stubs
│   ├── scenarios/                    # Synthetic generator & sensitivity tools
│   ├── utils/                        # Logging & YAML configuration
│   └── cli.py                        # Command Line Interface
├── data/                             # Datasets & Instances
│   ├── sample_delivery_data.csv      # Built-in Planar Cartesian 20-stop instance
│   ├── sample_delivery_geo.csv       # Built-in GPS WGS84 10-stop SF instance
│   └── raw/benchmark/                # Gold standard CVRPLIB & Solomon files
├── tests/                            # 80+ Pytest verification test suite
├── config.yaml                       # Global configuration
├── pyproject.toml                    # Package metadata & build definitions
└── requirements.txt                  # Pinned dependencies
```

---

## ⚡ 3. Key Features

- **5 Combinatorial Solvers**:
  1. *Nearest Neighbor*: Ultra-fast greedy baseline.
  2. *Clarke-Wright Savings*: Industry-standard construction heuristic.
  3. *Local Search Improvement*: Post-construction 2-opt, relocate, and exchange moves.
  4. *Google OR-Tools Metaheuristics*: Guided Local Search, Tabu Search, and Simulated Annealing.
  5. *Exact MILP*: Miller-Tucker-Zemlin (MTZ) formulation for small instances (≤12 stops).
- **Independent Validation Engine**: Recomputes all route distances, cumulative capacities, and arrival windows directly from raw node coordinates — zero trust in solver output declarations.
- **Multi-Objective Flexibility**: Optimize for minimum mileage, minimum active vehicles, or balanced duration.
- **Geographic Flexibility**: Full support for planar Cartesian $(X, Y)$ coordinates, Haversine Great-Circle distance, and OSRM road-network matrices.
- **Modern Dark Glassmorphism UI**: Polished Streamlit experience with interactive Plotly maps, diagnostic cards, and responsive metrics.

---

## 💻 4. Technologies & Frameworks

| Domain | Technology / Library |
| :--- | :--- |
| **Language** | Python 3.12+ (tested on Python 3.12 and 3.13) |
| **Constraint & Metaheuristic Optimization** | Google OR-Tools (`ortools>=9.8.0`) |
| **Exact Mathematical Programming** | SciPy HiGHS & PuLP (`scipy>=1.11.0`, `pulp>=2.7.0`) |
| **User Interface & Cartography** | Streamlit (`streamlit>=1.28.0`), Plotly (`plotly>=5.17.0`) |
| **Spatial & Numerical Computing** | NumPy, Pandas, GeoPandas, Shapely, PyProj |
| **Road Network Routing** | OpenStreetMap, OSMnx, OSRM API integration |
| **Testing & Quality Assurance** | PyTest (`pytest>=7.4.0`) |

---

## 📋 5. Prerequisites

Before installing, ensure your environment meets the following specifications:
- **Operating System**: Windows 10/11, macOS, or Linux.
- **Python**: Version `3.12` or `3.13` (64-bit).
- **Memory**: Minimum 4 GB RAM (8+ GB recommended for large instances).
- **Git**: Installed and available on your system path.

---

## 🚀 6. Installation & Environment Setup

Follow these steps to set up the project locally:

### Step 1: Open Terminal & Clone Repository
```powershell
# Open PowerShell (Windows) or Terminal (macOS/Linux)
git clone <your-repository-url>
cd ROUTEOPT
```

### Step 2: Create a Clean Virtual Environment
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

### Step 3: Install Required Dependencies
```powershell
# Upgrade core packaging tools
python -m pip install --upgrade pip setuptools wheel

# Install all dependencies and editable project package
pip install -e ".[dev]"

# OR install directly using requirements.txt
pip install -r requirements.txt
```

---

## 🖥️ 7. How to Run the Project

### Start the Streamlit Dashboard
```powershell
python -m streamlit run app/Home.py
```
After running this command, your terminal will display the local URL:
```text
  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```
Open **`http://localhost:8501`** in any modern web browser (Chrome, Edge, Firefox, Safari).

---

## 📖 8. Complete End-to-End User Guide

### Workflow Overview:
```text
[1. Delivery Data]  ──►  [2. Optimization]  ──►  [3. Route Map]  ──►  [4. Benchmarks]
  Upload CSV               Select Algorithm        Inspect Stops        Audit Trade-offs
  Load Sample              Tune Hyperparams        Check Schedule       Compare Models
```

### Step 1: Delivery Data Ingestion
1. Open the **Delivery Data** tab from the sidebar.
2. Choose one of three ingestion paths:
   - **Upload Custom CSV**: Drag and drop your `.csv` file.
   - **Built-in Sample Datasets**: Click `Load Sample Planar CSV` or `Load Sample Geo`.
   - **CVRPLIB & Solomon Benchmarks**: Load standardized instances like `A-n32-k5` or `Solomon C101`.
3. Configure your Fleet & Depot options:
   - **Coordinate System**: Choose `xy_planar` (for metric/arbitrary coordinates) or `wgs84` (for real lat/lon).
   - **Depot Selection**: Select `First row (index 0)`.
   - **Fleet Settings**: Set number of vehicles and payload capacity.
4. Click **`Validate & Build Instance Model`**.
5. Verify the green validation badge confirming constraint checks passed.

### Step 2: Solve the Routing Problem
1. Navigate to **Route Optimization** in the sidebar.
2. Select your desired solver:
   - For fast estimates: **Clarke-Wright Savings**.
   - For optimal operational quality: **Google OR-Tools**.
   - For tiny instances (≤12 stops): **Exact MILP**.
3. Tune the search budget (e.g., 15–30 seconds) and metaheuristic operator (*Guided Local Search* recommended).
4. Click **`Execute Optimization Run`**.
5. Review the solution summary: total distance, vehicles dispatched, fleet capacity utilization, and stop sequences.
6. Click **`Download Solution Manifest (JSON)`** to save the dispatch plan.

### Step 3: Cartography & Map Visualizer
1. Navigate to **Route Map**.
2. Examine the interactive color-coded vehicle circuits.
3. Hover over stops to view stop IDs, customer delivery demand, and visit sequences (`#1, #2...`).
4. Expand the **Detailed Stop-by-Stop Itinerary** table to inspect arrival times, departure times, and remaining payload balance.

### Step 4: Scenario Analysis & Stress Testing
1. Navigate to **Scenario Analysis**.
2. Select a parameter to sweep (e.g., `Customer Order Scale` or `Vehicle Payload Capacity`).
3. Enter test intervals (e.g., `10, 20, 30, 40, 50`) and choose the number of Monte Carlo seeds.
4. Click **`Run Monte Carlo Sweep`** to generate sensitivity curves illustrating mileage expansion and fleet utilization thresholds.

---

## 📁 9. Benchmark Datasets & Sample Data

### Expected CSV File Format
Your CSV file must include coordinates and demand numbers. The depot is placed at row 0 by default.

#### Format 1: Planar Cartesian (`xy_planar`)
```csv
customer_id,x,y,demand,service_time,earliest_time,latest_time
depot,40.0,50.0,0,0,0,1200
C1,45.0,68.0,10,10,60,300
C2,45.0,70.0,30,10,120,400
C3,42.0,66.0,10,10,90,360
C4,42.0,68.0,20,10,180,480
```

#### Format 2: GPS Latitude / Longitude (`wgs84`)
```csv
customer_id,lat,lon,demand,service_time,earliest_time,latest_time
depot,37.7749,-122.4194,0,0,0,720
C1,37.7833,-122.4167,15,10,30,240
C2,37.7690,-122.4467,25,10,60,300
C3,37.7558,-122.4200,20,10,90,360
```

#### Column Definitions:
| Column Name | Required | Description |
| :--- | :---: | :--- |
| `customer_id` | Yes | Unique identifier for the stop (e.g., `depot`, `C1`, `C2`) |
| `x` / `lon` | Yes | X coordinate or Longitude |
| `y` / `lat` | Yes | Y coordinate or Latitude |
| `demand` | Yes | Weight, volume, or package count (depot must have demand `0`) |
| `service_time` | No | Unloading dwell time at customer premises (minutes/units) |
| `earliest_time`| No | Earliest start of the delivery time window |
| `latest_time`  | No | Latest arrival deadline for the delivery time window |

*Pre-packaged sample files are available at `data/sample_delivery_data.csv` and `data/sample_delivery_geo.csv`.*

---

## ⌨️ 10. Command Line Interface (CLI)

RouteOpt provides a dedicated CLI for headless execution and batch evaluations:

```powershell
# Run the automated benchmark suite across CVRPLIB and Solomon sets
python -m routeopt.cli benchmark

# Specify custom directories
python -m routeopt.cli benchmark --cvrplib-dir data/raw/benchmark/cvrplib --output-dir reports
```
Outputs are written directly to:
- `reports/benchmark_results.json` (Structured test results)
- `reports/benchmark_summary.csv` (Spreadsheet summary)
- `reports/benchmark_report.md` (Markdown report with BKS gap percentages)

---

## 🧪 11. Testing & Validation

The project includes over **80 unit and integration tests** covering schema parsing, distance matrices, heuristics, OR-Tools constraints, and independent route validation.

```powershell
# Run all tests
python -m pytest tests/ -v

# Run specific modules
python -m pytest tests/test_algorithms.py -v
python -m pytest tests/test_ortools_solver.py -v
python -m pytest tests/test_loaders.py -v
python -m pytest tests/test_exact_milp.py -v
python -m pytest tests/test_scenarios.py -v
```

---

## 🔧 12. Troubleshooting Guide

### 1. `No module named streamlit` or `No module named pip` in venv
**Cause**: The virtual environment was initialized without standard packaging wheels or has a broken symlink.  
**Solution**:
```powershell
python -m ensurepip --upgrade
pip install -r requirements.txt
```
If the environment remains unlinked, rebuild it cleanly:
```powershell
deactivate
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. CSV Validation Error: `Coordinate columns not found`
**Cause**: The uploaded CSV column headers do not match the expected names.  
**Solution**:
- Ensure Planar datasets use lowercase headers `x` and `y`.
- Ensure GPS datasets use lowercase headers `lat` and `lon` (or `latitude` / `longitude`).
- Select the matching **Coordinate System** dropdown option (`xy_planar` vs `wgs84`) on the Delivery Data page.

### 3. Solver Failure / Infeasibility Warning
**Cause**: Fleet capacity or time windows are mathematically impossible to satisfy.  
**Solution**:
- Verify that customer demands do not exceed the vehicle payload capacity ($d_i \le Q$).
- Check if total customer demand divided by capacity exceeds the allocated number of trucks ($N_{veh} \ge \lceil \sum d_i / Q \rceil$).
- Increase fleet size or adjust vehicle capacity in the configuration sidebar.

### 4. Exact MILP Solver Freezes
**Cause**: MTZ formulations are NP-hard. An instance with $>12$ customers creates millions of constraints.  
**Solution**: Use **Google OR-Tools** or **Clarke-Wright Savings** for instances with $>12$ customers.

---

## 📄 13. License

This project is licensed under the **MIT License**. You are free to use, modify, distribute, and integrate this software in research and commercial projects.
