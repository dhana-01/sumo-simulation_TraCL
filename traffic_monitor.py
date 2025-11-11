# Step 1: Add modules to provide access to specific libraries and functions
import os
import sys

# Step 2: Establish path to SUMO (SUMO_HOME)
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# Step 3: Add TraCI module
import traci

# Step 4: Define SUMO Configuration
# Use your config file and its 0.1s step-length
Sumo_config = [
    'sumo-gui',
    '-c', 'simu1.sumocfg',
    '--step-length', '0.1',
    '--start'
]

# Step 5: Open connection between SUMO and TraCI
try:
    traci.start(Sumo_config)
except Exception as e:
    print(f"Error starting TraCI: {e}")
    sys.exit("Could not connect to SUMO. Is SUMO_HOME set correctly?")


# Step 6: Define Variables
step_count = 0

# --- Variables adapted for your simu1.net.xml file ---
APPROACH_EDGES = ["north_in", "south_in", "east_in", "west_in"]

SEGMENT_MAP = {
    "north_in": 3,  # 302.26m long
    "south_in": 3,  # 302.79m long
    "east_in":  2,  # 192.46m long
    "west_in":  3   # 303.29m long
}

# --- Time-based Loop Variables ---
STEP_LENGTH = 0.1  # Must match your .sumocfg and Step 4
TOTAL_SIMULATION_TIME_SEC = 300  # 5 minutes
DATA_INTERVAL_SEC = 30  # Get data every 30 seconds

# Calculate steps
TOTAL_STEPS = int(TOTAL_SIMULATION_TIME_SEC / STEP_LENGTH)  # 300 / 0.1 = 3000 steps
DATA_INTERVAL_STEPS = int(DATA_INTERVAL_SEC / STEP_LENGTH) # 30 / 0.1 = 300 steps


# Step 7: Define Functions

def categorize_traffic(avg_speed):
    """
    Categorizes the traffic state based on average speed.
    (This function is from your sample script)
    """
    # Approximate congestion thresholds (adjust to your scenario)
    # Note: Your .net.xml file has a speed limit of 13.89 m/s
    if avg_speed >= 10:
        return "NORMAL"
    elif 5 <= avg_speed < 10:
        return "SLOW"
    else:
        # This will also catch the '0' speed for TRAFFIC_JAM
        return "TRAFFIC_JAM"

def get_segment_data(detector_id):
    """
    Gets the vehicle count and average speed for a single 100m segment.
    """
    try:
        # These are the TraCI calls that fetch data from your .add.xml file
        avg_speed = traci.lanearea.getLastStepMeanSpeed(detector_id)
        veh_count = traci.lanearea.getLastStepVehicleNumber(detector_id)
        
        # If no cars are on the detector, speed is -1.
        if veh_count == 0 or avg_speed < 0:
            return 0, 0.0  # Return 0 vehicles and 0.0 speed
            
        return veh_count, avg_speed
        
    except Exception as e: 
        print(f"Error in get_segment_data (detector '{detector_id}'): {e}")
        print("  This likely means the detector ID is wrong or wasn't loaded.")
        return 0, 0.0 # Return 0, 0 to avoid crashing

# Step 8: Take simulation steps for exactly 5 minutes
print(f"Simulation starting... Running for {TOTAL_SIMULATION_TIME_SEC} seconds ({TOTAL_STEPS} steps).")
print(f"Reporting data every {DATA_INTERVAL_SEC} seconds ({DATA_INTERVAL_STEPS} steps).")
print("\n")

try:
    for step in range(TOTAL_STEPS):
        traci.simulationStep()
        step_count += 1
        
        # Check if it's time to print data (every 300 steps = 30 seconds)
        if step_count % DATA_INTERVAL_STEPS == 0 and step_count > 0:
            
            current_time = step_count * STEP_LENGTH
            print(f"--- Simulation Time: {current_time:.1f}s ---")
            
            for edge in APPROACH_EDGES:
                try: 
                    polyline_output = []
                    num_segments = SEGMENT_MAP[edge]
                    
                    for i in range(1, num_segments + 1):
                        # Construct the detector ID, e.g., "north_in_seg_1"
                        detector_id = f"{edge}_seg_{i}"
                        
                        # Get the data from the 100m detector
                        veh, speed = get_segment_data(detector_id)
                        
                        # Use your function to get the traffic state
                        state = categorize_traffic(speed)
                        
                        polyline_output.append(f"Seg{i}: {state} ({veh} veh, {speed:.2f} m/s)")
                    
                    print(f"Edge: {edge.upper()}")
                    print("  | ".join(polyline_output))
                    print("-" * 20)
                    
                except Exception as e: 
                    print(f"CRITICAL Error processing edge '{edge}': {e}")
            
            print("\n") # Add a blank line for readability

except traci.TraCIException as e:
    print(f"A TraCI error occurred during simulation: {e}")
except Exception as e:
    print(f"A general Python error occurred: {e}")

# Step 9: Close connection
finally:
    traci.close()
    print(f"Simulation Completed after {TOTAL_SIMULATION_TIME_SEC} seconds!")