import cv2
import time
import os
import pyzed.sl as sl

def run_dual_capture(duration_sec=300, output_fps=30):
    # --- 0. Define Directory Paths ---
    base_dir = r"C:\Users\amirm\Documents\RodeOS\rodeos-core\MediaCapture"
    rgb_dir = os.path.join(base_dir, "RGB")
    zed_footage_dir = os.path.join(base_dir, "ZED", "Footage")
    zed_data_dir = os.path.join(base_dir, "ZED", "Data")

    # Ensure all required folders exist
    os.makedirs(rgb_dir, exist_ok=True)
    os.makedirs(zed_footage_dir, exist_ok=True)
    os.makedirs(zed_data_dir, exist_ok=True)

    # --- 1. Initialize ZED Mini ---
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.camera_fps = output_fps
    init_params.depth_mode = sl.DEPTH_MODE.NEURAL  # High-accuracy depth for biophysical tracking
    init_params.coordinate_units = sl.UNIT.METER

    err = zed.open(init_params)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open ZED Mini: {err}")
        return

    # Enable native ZED SVO recording to save complete depth & camera data stream
    svo_output_path = os.path.join(zed_data_dir, "zed_data_stream.svo")
    recording_params = sl.RecordingParameters()
    recording_params.video_filename = svo_output_path
    recording_params.compression_mode = sl.SVO_COMPRESSION_MODE.H264
    
    err = zed.enable_recording(recording_params)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to enable ZED data recording: {err}")
        zed.close()
        return

    # --- 2. Initialize Ordinary Webcam (Index 1 for external webcam) ---
    cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # Use cv2.CAP_DSHOW on Windows for fast init
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, output_fps)

    if not cap.isOpened():
        print("Error: Could not open ordinary webcam at index 1. Trying index 2...")
        cap.release()
        cap = cv2.VideoCapture(2, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, output_fps)
        
        if not cap.isOpened():
            print("Error: Could not open external webcam on index 1 or 2.")
            zed.disable_recording()
            zed.close()
            return

    # --- 3. Setup Video Writers ---
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    zed_footage_path = os.path.join(zed_footage_dir, 'zed_rgb_output.mp4')
    webcam_output_path = os.path.join(rgb_dir, 'webcam_output.mp4')

    zed_writer = cv2.VideoWriter(zed_footage_path, fourcc, output_fps, (1280, 720))
    webcam_writer = cv2.VideoWriter(webcam_output_path, fourcc, output_fps, (1280, 720))

    zed_image = sl.Mat()
    zed_depth = sl.Mat()
    runtime_params = sl.RuntimeParameters()

    print(f"Starting synchronized capture for {duration_sec} seconds...")
    start_time = time.time()
    frame_count = 0

    try:
        while (time.time() - start_time) < duration_sec:
            loop_start = time.time()

            # Capture ZED frame (automatically records to SVO data stream when grab succeeds)
            if zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(zed_image, sl.VIEW.LEFT)
                zed.retrieve_measure(zed_depth, sl.MEASURE.DEPTH)
                
                # Convert ZED sl.Mat to OpenCV cv.Mat for RGB footage file
                zed_frame_ocv = zed_image.get_data()
                zed_bgr = cv2.cvtColor(zed_frame_ocv, cv2.COLOR_BGRA2BGR)
                zed_writer.write(zed_bgr)

            # Capture Ordinary Webcam frame
            ret, webcam_frame = cap.read()
            if ret:
                if webcam_frame.shape[:2] != (720, 1280):
                    webcam_frame = cv2.resize(webcam_frame, (1280, 720))
                webcam_writer.write(webcam_frame)

            frame_count += 1

            # Maintain target framerate timing
            elapsed = time.time() - loop_start
            target_period = 1.0 / output_fps
            if elapsed < target_period:
                time.sleep(target_period - elapsed)

    except Exception as e:
        print(f"Capture interrupted: {e}")

    # --- 4. Cleanup ---
    zed.disable_recording()
    zed.close()
    cap.release()
    zed_writer.release()
    webcam_writer.release()
    print(f"Capture complete. Saved {frame_count} frames successfully.")
    print(f"All files organized under: {base_dir}")

if __name__ == "__main__":
    run_dual_capture(duration_sec=300)