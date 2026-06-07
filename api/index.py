# api/index.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import statistics

app = FastAPI()

# Requirement 3: Enable CORS for POST requests
# This allows any website dashboard to safely talk to your API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Requirement 1: Accept a POST request with specific JSON body
# We create a 'Pydantic Model' to tell FastAPI exactly what data to expect.
class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: int

# We load the JSON file right when the server spins up.
# We look in the folder *above* the 'api' folder to find it.
file_path = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")
try:
    with open(file_path, "r") as f:
        # NOTE: This assumes your JSON is a list of dictionaries like: 
        # [{"region": "amer", "latency": 150, "uptime": 0.99}, ...]
        # If your JSON has different names, update the strings below!
        telemetry_data = json.load(f)
except Exception:
    telemetry_data = []

# Helper function: Calculate the 95th Percentile (p95)
# This means "95% of the wait times were faster than THIS number"
def get_p95(data_list):
    if not data_list: return 0
    sorted_data = sorted(data_list)
    index = int(len(sorted_data) * 0.95) # Find the 95% mark
    if index >= len(sorted_data):
        index = len(sorted_data) - 1
    return sorted_data[index]

# Requirement 2: Return per-region metrics
@app.post("/")
def calculate_metrics(req: AnalyticsRequest):
    results = {}
    
    # Loop through the regions they asked for (e.g., "amer", "emea")
    for region in req.regions:
        
        # 1. Filter out only the data for this specific region
        region_records = [item for item in telemetry_data if item.get("region") == region]
        
        if not region_records:
            results[region] = {"error": "No data found"}
            continue
            
        # 2. Extract just the lists of numbers we need
        latencies = [item["latency"] for item in region_records if "latency" in item]
        uptimes = [item["uptime"] for item in region_records if "uptime" in item]
        
        # 3. Do the math
        avg_latency = statistics.mean(latencies) if latencies else 0
        avg_uptime = statistics.mean(uptimes) if uptimes else 0
        p95_latency = get_p95(latencies)
        
        # 4. Count Breaches: How many latencies were higher than the allowed threshold?
        breaches = sum(1 for lat in latencies if lat > req.threshold_ms)
        
        # 5. Pack the results into the required format
        results[region] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_uptime": avg_uptime,
            "breaches": breaches
        }
        
    return results
