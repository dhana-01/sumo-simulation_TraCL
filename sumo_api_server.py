# sumo_traci_server.py
import os
import sys
import traci
import json
import threading
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List, Any
import uvicorn

# === SUMO Setup ===
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

app = FastAPI(title="SUMO TraCI Real-time Server", version="1.0")

# Global state
simulation_thread = None
is_running = False
latest_data = {}
lock = threading.Lock()

# Your simulation constants (from your script)
APPROACH_EDGES = ["north_in", "south_in", "east_in", "west_in"]
SEGMENT_LENGTHS = {
    "north_in": [100.0, 100.0, 102.26],
    "south_in": [100.0, 100.0, 102.79],
    "east_in":  [100.0, 92.46],
    "west_in":  [100.0, 100.0, 103.29]
}
SPEED_LIMIT = 13.89
STEP_LENGTH = 0.1
DATA_INTERVAL_SEC = 30
DATA_INTERVAL_STEPS = int(DATA_INTERVAL_SEC / STEP_LENGTH)

# === Your original functions (exactly as you wrote) ===
def categorize_traffic(avg_speed: float) -> str:
    if avg_speed >= 10:
        return "NORMAL"
    elif 5 <= avg_speed < 10:
        return "SLOW"
    else:
        return "TRAFFIC_JAM"

def get_segment_data(detector_id: str):
    try:
        avg_speed = traci.lanearea.getLastStepMeanSpeed(detector_id)
        veh_count = traci.lanearea.getLastStepVehicleNumber(detector_id)
        if veh_count == 0 or avg_speed < 0:
            return 0, 0.0
        return veh_count, avg_speed
    except:
        return 0, 0.0

def calculate_route_metrics(edge_id: str, segment_lengths: List[float]) -> Dict[str, Any]:
    total_vehicles = 0
    total_travel_time = 0.0
    total_distance = sum(segment_lengths)
    weighted_speed_sum = 0.0
    total_weight = 0.0

    for i, length in enumerate(segment_lengths):
        detector_id = f"{edge_id}_seg_{i + 1}"
        veh, speed = get_segment_data(detector_id)
        total_vehicles += veh
        effective_speed = max(speed, 0.1)
        total_travel_time += length / effective_speed
        weighted_speed_sum += speed * length
        total_weight += length

    avg_route_speed = weighted_speed_sum / total_weight if total_weight > 0 else 0.0
    free_flow_time = total_distance / SPEED_LIMIT
    delay = max(0.0, total_travel_time - free_flow_time)
    congestion_level = categorize_traffic(avg_route_speed)

    return {
        "edge": edge_id,
        "vehicle_count": total_vehicles,
        "avg_speed": round(avg_route_speed, 2),
        "travel_time": round(total_travel_time, 2),
        "delay": round(delay, 2),
        "congestion": congestion_level
    }

def collect_all_data() -> Dict:
    results = {}
    for edge in APPROACH_EDGES:
        lengths = SEGMENT_LENGTHS[edge]
        results[edge] = calculate_route_metrics(edge, lengths)
    results["simulation_time"] = traci.simulation.getTime()
    return results

# === Simulation Runner ===
def run_simulation():
    global is_running, latest_data

    traci.start([
        'sumo-gui', '-c', 'simu1.sumocfg',
        '--step-length', '0.1', '--start'
    ])
    is_running = True
    step = 0

    print("SUMO Simulation STARTED via TraCI Server")

    try:
        while is_running and traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            step += 1

            if step % DATA_INTERVAL_STEPS == 0:
                with lock:
                    latest_data = collect_all_data()
                print(f"Data updated at {traci.simulation.getTime():.1f}s")

    except Exception as e:
        print(f"Simulation error: {e}")
    finally:
        traci.close()
        is_running = False
        print("Simulation ENDED")

# === API Endpoints ===
@app.get("/")
def home():
    return {"message": "SUMO TraCI Server Running", "status": "ok"}

@app.get("/start")
def start_simulation():
    global simulation_thread
    if is_running:
        return {"status": "already_running"}
    simulation_thread = threading.Thread(target=run_simulation, daemon=True)
    simulation_thread.start()
    return {"status": "started"}

@app.get("/stop")
def stop_simulation():
    global is_running
    is_running = False
    return {"status": "stopping"}

@app.get("/data")
def get_data():
    with lock:
        if latest_data:
            return latest_data
        return {"error": "No data yet. Simulation may not have started or reached 30s."}

@app.get("/status")
def status():
    return {
        "running": is_running,
        "time": traci.simulation.getTime() if is_running else 0,
        "has_data": bool(latest_data)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)