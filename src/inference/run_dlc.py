# src/inference/run_dlc.py
import os
import glob
import deeplabcut

def run_inference(config_path, frames_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    # Verify config exists
    if not os.path.exists(config_path):
        print(f"Error: DLC config not found at {config_path}")
        return

    print(f"Running DeepLabCut inference on frames in: {frames_dir}")
    
    # Run DLC evaluation/inference on the folder of extracted frames
    deeplabcut.analyze_videos(
        config_path,
        [frames_dir],
        destfolder=output_dir,
        save_as_csv=True
    )
    
    print(f"Inference complete! Results saved to {output_dir}")

if __name__ == "__main__":
    print("=== DeepLabCut Batch Inference Bridge ===")
    
    # Prompt for your DLC project config path
    config_path = input("Enter path to your DLC config.yaml: ").strip().strip('"')
    
    # Target your newly extracted frames directory
    default_frames = os.path.join("Rodeos_vivox", "FramesOut")
    frames_dir = input(f"Enter frames directory [default: {default_frames}]: ").strip().strip('"')
    if not frames_dir:
        frames_dir = default_frames
        
    output_dir = os.path.join(frames_dir, "dlc_results")
    
    run_inference(config_path, frames_dir, output_dir)