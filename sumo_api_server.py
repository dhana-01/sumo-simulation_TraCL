"""
FastAPI server to control and monitor a SUMO traffic simulation via a REST API.

This server uses TraCI to interface with a running SUMO instance. It allows for
starting, stepping through, and stopping the simulation, as well as retrieving
real-time traffic data from configured lane area detectors.
"""
import traci
from fastapi import FastAPI, HTTPException
import uvicorn
import time # Import the time module

# --- 1. Configuration ---
SUMO_CMD = ["sumo-gui", "-c", "simu1.sumocfg"]

DETECTOR_CONFIG = {
    "north_in": ["north_in_seg_1", "north_in_seg_2", "north_in_seg_3"],
    "south_in": ["south_in_seg_1", "south_in_seg_2", "south_in_seg_3"],
    "east_in":  ["east_in_seg_1", "east_in_seg_2"],
    "west_in":  ["west_in_seg_1", "west_in_seg_2", "west_in_seg_3"]
}

app = FastAPI(title="SUMO Traffic Simulation API")

# (Helper functions are the same and robust, no changes needed)
def categorize_traffic(avg_speed):
    """Categorizes traffic flow based on average speed.

    Args:
        avg_speed (float): The average speed of vehicles in meters per second.

    Returns:
        str: A string representing the traffic status ('NORMAL', 'SLOW', 'TRAFFIC_JAM').
    """
    if avg_speed >= 10: return "NORMAL"
    elif 5 <= avg_speed < 10: return "SLOW"
    else: return "TRAFFIC_JAM"

def get_segment_data(detector_id):
    """Retrieves and processes data from a specific SUMO lane area detector."""
    try:
        avg_speed = traci.lanearea.getLastStepMeanSpeed(detector_id)
        veh_count = traci.lanearea.getLastStepVehicleNumber(detector_id)
        if veh_count == 0 or avg_speed < 0:
            return {"status": "EMPTY", "vehicle_count": 0, "avg_speed_mps": 0.0}
        status = categorize_traffic(avg_speed)
        return {"status": status, "vehicle_count": veh_count, "avg_speed_mps": round(avg_speed, 2)}
    except traci.TraCIException:
        return {"error": f"TraCI connection lost for detector '{detector_id}'."}

# --- API Endpoints ---
@app.get("/", tags=["General"])
def read_root():
    """Root endpoint providing a welcome message and a link to the API docs."""
    return {"message": "SUMO API Server is running. Go to /docs to see the API."}

@app.post("/simulation/start", tags=["Simulation Control"])
def start_simulation():
    """Starts the SUMO simulation using the pre-configured command.
    """
    try:
        traci.start(SUMO_CMD)
        # Add a small delay to ensure SUMO is fully initialized before Colab sends the next command
        time.sleep(1)
        return {"message": "SUMO simulation started."}
    except Exception as e:
        # Catch any potential error during startup
        return HTTPException(status_code=500, detail=f"Failed to start SUMO: {e}")

@app.post("/simulation/step", tags=["Simulation Control"])
def simulation_step():
    """Advances the SUMO simulation by a single step."""
    try:
        if traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            return {"simulation_active": True}
        else:
            traci.close()
            return {"simulation_active": False, "message": "Simulation finished."}
    except traci.TraCIException:
        return {"simulation_active": False, "message": "TraCI connection not found."}

@app.get("/traffic_data", tags=["Traffic Data"])
def get_all_traffic_data():
    """Retrieves traffic data from all configured lane area detectors."""
    all_data = {}
    for edge_name, detector_ids in DETECTOR_CONFIG.items():
        edge_segments = []
        for i, det_id in enumerate(detector_ids):
            segment_data = get_segment_data(det_id)
            segment_data["segment_name"] = f"Seg{i+1}"
            edge_segments.append(segment_data)
        all_data[edge_name] = edge_segments
    return all_data

@app.post("/simulation/stop", tags=["Simulation Control"])
def stop_simulation():
    """Stops the active SUMO simulation and closes the TraCI connection."""
    try:
        traci.close()
        return {"message": "Active SUMO simulation has been stopped."}
    except traci.TraCIException:
        return {"message": "No active simulation was running."}

if __name__ == "__main__":
    """Main execution block to run the FastAPI server using uvicorn."""
    uvicorn.run(app, host="127.0.0.1", port=8000)