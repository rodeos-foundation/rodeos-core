# src/bridge/zmq_streamer.py
import zmq
import time
import pandas as pd
import os

def stream_skeleton_telemetry(csv_path, port=5555):
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{port}")
    print(f"Broadcasting rodent tracking telemetry on port {port}...")
    
    if not os.path.exists(csv_path):
        print(f"CSV path {csv_path} not found.")
        return
        
    df = pd.read_csv(csv_path, header=[1, 2], index_col=0)
    
    for frame_idx, row in df.iterrows():
        payload = {
            "frame": int(frame_idx),
            "timestamp": time.time(),
            "joints": {}
        }
        
        for bodypart in df.columns.levels[0]:
            x = row[(bodypart, 'x')]
            y = row[(bodypart, 'y')]
            likelihood = row[(bodypart, 'likelihood')]
            payload["joints"][bodypart] = {"x": float(x), "y": float(y), "conf": float(likelihood)}
            
        socket.send_json(payload)
        time.sleep(1.0 / 30.0)

if __name__ == "__main__":
    sample_csv = "sample_dlc_output.csv"
    if os.path.exists(sample_csv):
        stream_skeleton_telemetry(sample_csv)