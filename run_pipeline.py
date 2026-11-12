import os
import glob
import shutil
import deeplabcut

# Dynamically locate config.yaml
config_files = glob.glob(r"C:\Users\zaukt\Projects\rodeos\RodeosTracking-SwarmoscopeTech-SwarmoscopeTech-*\config.yaml")
if not config_files:
    raise FileNotFoundError("Could not find generated DeepLabCut project config.yaml")
config_path = config_files[0]
project_dir = os.path.dirname(config_path)
print(f"Using config: {config_path}")

# 1. Extract frames (only if not already extracted to prevent frame re-clustering desync)
print("\n--- Step 1: Extracting Training Frames ---")
try:
    deeplabcut.extract_frames(config_path, mode='automatic', algo='kmeans', userfeedback=False)
except Exception as e:
    print(f"Extraction note: {e}")

# 2. Open labeling GUI to generate correct native MultiIndex H5/CSV annotation tables
print("\n--- Step 2: Opening Labeling GUI ---")
print("Please label your frames in the GUI, save, and close the window to continue training.")
deeplabcut.label_frames(config_path)

# 3. Purge stale outputs from previous runs to prevent index desync and cache pollution
print("\n--- Step 3: Clearing Stale Outputs ---")
for target in ["training-datasets", "dlc-models-pytorch"]:
    target_path = os.path.join(project_dir, target)
    if os.path.exists(target_path):
        shutil.rmtree(target_path)
        print(f"Cleared stale directory: {target}")

# 4. Compile Training Dataset using the newly validated annotations
print("\n--- Step 4: Compiling Training Dataset ---")
deeplabcut.create_training_dataset(config_path)

# 5. Train Network using modern PyTorch epochs parameter
print("\n--- Step 5: Starting Model Training ---")
deeplabcut.train_network(config_path, epochs=200, display_iters=100)