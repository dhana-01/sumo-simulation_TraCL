# Step 1: Add modules to provide access to specific libraries and functions
import os
import sys
from typing import Dict, List, Tuple, Any

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

# Define segment lengths for accurate calculations (from simu1.add.xml)
# Format: edge_id: [length_seg_1, length_seg_2, ...]
SEGMENT_LENGTHS: Dict[str, List[float]] = {
    "north_in": [100.0, 100.0, 102.26],
    "south_in": [100.0, 100.0, 102.79],
    "east_in":  [100.0, 92.46],
    "west_in":  [100.0, 100.0, 103.29]
}

SPEED_LIMIT = 13.89  # m/s (approx 50 km/h)

# --- Time-based Loop Variables ---
STEP_LENGTH = 0.1  # Must match your .sumocfg and Step 4
TOTAL_SIMULATION_TIME_SEC = 300  # 5 minutes
DATA_INTERVAL_SEC = 30  # Get data every 30 seconds

# Calculate steps
TOTAL_STEPS = int(TOTAL_SIMULATION_TIME_SEC / STEP_LENGTH)  # 300 / 0.1 = 3000 steps
DATA_INTERVAL_STEPS = int(DATA_INTERVAL_SEC / STEP_LENGTH) # 30 / 0.1 = 300 steps


# Step 7: Define Functions

def categorize_traffic(avg_speed: float) -> str:
    """
    Categorizes the traffic state based on average speed.
    
    Args:
        avg_speed (float): The average speed in m/s.
        
    Returns:
        str: The congestion level ('NORMAL', 'SLOW', 'TRAFFIC_JAM').
    """
    if avg_speed >= 10:
        return "NORMAL"
    elif 5 <= avg_speed < 10:
        return "SLOW"
    else:
        return "TRAFFIC_JAM"

def get_segment_data(detector_id: str) -> Tuple[int, float]:
    """
    Gets the vehicle count and average speed for a single lane area detector.
    
    Args:
        detector_id (str): The ID of the lane area detector.
        
    Returns:
        Tuple[int, float]: A tuple containing (vehicle_count, average_speed).
    """
    try:
        avg_speed = traci.lanearea.getLastStepMeanSpeed(detector_id)
        veh_count = traci.lanearea.getLastStepVehicleNumber(detector_id)
        
        # If no cars are on the detector, speed is -1.
        if veh_count == 0 or avg_speed < 0:
            return 0, 0.0
            
        return veh_count, avg_speed
        
    except Exception as e: 
        print(f"Error in get_segment_data (detector '{detector_id}'): {e}")
        return 0, 0.0

def calculate_route_metrics(edge_id: str, segment_lengths: List[float]) -> Dict[str, Any]:
    """
    Calculates aggregated metrics for a specific route (edge).
    
    Args:
        edge_id (str): The edge ID (e.g., 'north_in').
        segment_lengths (List[float]): List of lengths for each segment on this edge.
        
    Returns:
        Dict[str, Any]: Dictionary containing route metrics.
    """
    total_vehicles = 0
    total_travel_time = 0.0
    total_distance = sum(segment_lengths)
    weighted_speed_sum = 0.0
    total_weight = 0.0
    
    num_segments = len(segment_lengths)
    
    for i in range(num_segments):
        # Construct the detector ID, e.g., "north_in_seg_1"
        # Note: range is 0-indexed, but segments are 1-indexed in XML
        detector_id = f"{edge_id}_seg_{i + 1}"
        length = segment_lengths[i]
        
        veh, speed = get_segment_data(detector_id)
        
        total_vehicles += veh
        
        # Calculate Travel Time for this segment
        # If speed is 0 (jam), assume a very low speed (e.g., 0.1 m/s) to avoid division by zero
        # or use a max travel time cap. Here we use 0.1 m/s as a proxy for crawling.
        effective_speed = max(speed, 0.1)
        segment_travel_time = length / effective_speed
        total_travel_time += segment_travel_time
        
        # Weighted Average Speed Calculation
        # We weight by segment length to get a representative speed for the whole route
        weighted_speed_sum += speed * length
        total_weight += length

    avg_route_speed = weighted_speed_sum / total_weight if total_weight > 0 else 0.0
    
    # Calculate Delay
    # Free flow time = Distance / Speed Limit
    free_flow_time = total_distance / SPEED_LIMIT
    delay = max(0.0, total_travel_time - free_flow_time)
    
    congestion_level = categorize_traffic(avg_route_speed)
    
    return {
        "edge": edge_id,
        "vehicle_count": total_vehicles,
        "avg_speed": avg_route_speed,
        "travel_time": total_travel_time,
        "delay": delay,
        "congestion": congestion_level
    }

# Step 8: Take simulation steps for exactly 5 minutes
print(f"Simulation starting... Running for {TOTAL_SIMULATION_TIME_SEC} seconds ({TOTAL_STEPS} steps).")
print(f"Reporting data every {DATA_INTERVAL_SEC} seconds ({DATA_INTERVAL_STEPS} steps).")
print("\n")

try:
    for step in range(TOTAL_STEPS):
        traci.simulationStep()
        step_count += 1
        
        # Check if it's time to print data
        if step_count % DATA_INTERVAL_STEPS == 0 and step_count > 0:
            
            current_time = step_count * STEP_LENGTH
            print(f"--- Simulation Time: {current_time:.1f}s ---")
            print(f"{'ROUTE':<10} | {'STATUS':<12} | {'VEHICLES':<8} | {'SPEED (m/s)':<12} | {'TIME (s)':<10} | {'DELAY (s)':<10}")
            print("-" * 80)
            
            for edge in APPROACH_EDGES:
                try: 
                    lengths = SEGMENT_LENGTHS[edge]
                    metrics = calculate_route_metrics(edge, lengths)
                    
                    print(f"{metrics['edge']:<10} | "
                          f"{metrics['congestion']:<12} | "
                          f"{metrics['vehicle_count']:<8} | "
                          f"{metrics['avg_speed']:<12.2f} | "
                          f"{metrics['travel_time']:<10.1f} | "
                          f"{metrics['delay']:<10.1f}")
                    
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