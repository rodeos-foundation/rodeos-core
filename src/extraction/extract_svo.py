# src/extraction/extract_svo.py
import pyzed.sl as sl
import sys
import os

def extract_svo(svo_path, output_dir):
    if not os.path.exists(svo_path):
        print(f"Error: File not found at {svo_path}")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    init_params = sl.InitParameters()
    init_params.set_from_svo_file(svo_path)
    # Removed iterable_extraction line here
    
    zed = sl.Camera()
    status = zed.open(init_params)
    if status != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open SVO file {svo_path}: {status}")
        return
        
    runtime_params = sl.RuntimeParameters()
    image = sl.Mat()
    
    i = 0
    print(f"Extracting frames from {svo_path} into {output_dir}...")
    while zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
        zed.retrieve_image(image, sl.VIEW.LEFT)
        frame_path = os.path.join(output_dir, f"frame_{i:05d}.png")
        image.write(frame_path)
        i += 1
        
    zed.close()
    print(f"Successfully extracted {i} frames to {output_dir}")

if __name__ == "__main__":
    print("=== ZED SVO2 Frame Extractor ===")
    
    svo_path = input("Enter the path to your .svo2 file (e.g., Rodeos_vivox/side_view.svo2): ").strip().strip('"')
    
    if not svo_path:
        print("No path provided. Exiting.")
        sys.exit(1)
        
    base_name = os.path.splitext(os.path.basename(svo_path))[0]
    default_output = os.path.join("Rodeos_vivox", f"frames_{base_name}")
    
    output_dir = input(f"Enter output directory for frames [default: {default_output}]: ").strip().strip('"')
    if not output_dir:
        output_dir = default_output
        
    extract_svo(svo_path, output_dir)