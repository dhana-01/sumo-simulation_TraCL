# SUMO Traffic Simulation & API

This project implements a traffic simulation using [SUMO (Simulation of Urban MObility)](https://eclipse.dev/sumo/) and provides a Python interface for monitoring and controlling the simulation. It features a standalone monitoring script and a FastAPI-based server for real-time data access and simulation control.

## Features

*   **Traffic Simulation**: Custom SUMO network (`simu1.net.xml`) with defined routes and traffic flows.
*   **Real-time Monitoring**: `traffic_monitor.py` tracks vehicle counts, average speeds, and congestion levels across different segments.
*   **REST API**: `sumo_api_server.py` exposes endpoints to:
    *   Start, stop, and step through the simulation.
    *   Retrieve real-time traffic data (vehicle counts, speeds, congestion status).
    *   Check simulation status.
*   **Data Analysis**: Calculates metrics such as travel time, delay, and categorizes traffic flow (Normal, Slow, Traffic Jam).

## Prerequisites

*   **Python 3.8+**
*   **SUMO**: Ensure SUMO is installed and the `SUMO_HOME` environment variable is set.
*   **uv**: Install uv package manager:
    ```powershell
    # Windows (PowerShell)
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```
    ```bash
    # macOS/Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

## Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    ```
2.  Navigate to the project directory:
    ```bash
    cd SUMO_Traffic_Simulation
    ```
3.  **First-time setup** - Create virtual environment and install dependencies:
    ```bash
    uv sync
    ```
    This creates a `.venv/` directory and installs all dependencies from `uv.lock`.

## Usage

### 1. Running the Traffic Monitor
To run the standalone monitoring script:
```bash
uv run python traffic_monitor.py
```

### 2. Running the API Server
To start the FastAPI server:
```bash
uv run uvicorn sumo_api_server:app --host 127.0.0.1 --port 8000
```
Or alternatively:
```bash
uv run python sumo_api_server.py
```
*   The server will start at `http://127.0.0.1:8000`.
*   Interactive API documentation (Swagger UI) is available at `http://127.0.0.1:8000/docs`.

### 3. Managing Dependencies
To add a new dependency:
```bash
uv add <package-name>
```
To update dependencies:
```bash
uv sync
```

### API Endpoints
*   `GET /`: Server status.
*   `GET /start`: Start the SUMO simulation.
*   `GET /stop`: Stop the simulation.
*   `GET /data`: Get current traffic data (vehicle counts, speeds, etc.).
*   `GET /status`: Check if simulation is running.

## Project Structure

*   `simu1.sumocfg`: Main SUMO configuration file.
*   `simu1.net.xml`: Network definition (roads, intersections).
*   `simu1.rou.xml`: Vehicle routes definition.
*   `simu1.add.xml`: Additional elements (detectors).
*   `traffic_monitor.py`: Script for monitoring traffic metrics.
*   `sumo_api_server.py`: FastAPI server implementation.
