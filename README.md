# RodeOS

**The Open-Source Operating System for Biological Simulation**

RodeOS is an open-source platform connecting experimental data, biological simulation environments, AI agents, and phenotype detection. Our mission is to create an interoperable infrastructure that enables researchers and developers to reproduce biological scenarios, simulate phenotypic outcomes, and train more reliable detection systems.

## The Vision

**From Real Experiments to Simulation and Back.**

RodeOS establishes a continuous loop between:
- **Observe** - Capture and structure experimental observations.
- **Simulate** - Reproduce biological scenarios in virtual environments.
- **Train** - Develop and validate AI models using real and synthetic data.
- **Validate** - Compare simulated outcomes against experimental evidence.

## Core Architecture

- **Coordinators** - Orchestrate experiments and simulation workflows.
- **Assays** - Define experimental protocols and conditions.
- **Observations** - Measured biological events and phenotypes.
- **Arguments** - Manage parameters, hypotheses, and simulation inputs.
- **Flows** - Connect the components into reproducible workflows.

## Technology

RodeOS integrates:
- **Unreal Engine-based biological simulation (`RodeOSsim`)** - C++ and Blueprint simulation environment (`ARatLandmarkTracker`, skeletal rigs, and marker orchestration) built on Unreal Engine 5.9 (`RodeOS.uproject`).
- **Computer vision and machine learning** - DeepLabCut pose estimation (`rodeos-analysis` with PyTorch `2.5.1+cu121` and DeepLabCut `3.0.2` on Windows, plus legacy TensorFlow `2.15.1` / DLC `2.3.0` workflows in WSL2/Ubuntu `amber` and SLEAP `1.6.6` in `sleap`).
- **Experimental data management** - Standardized pose and observation outputs (`.h5`, `.csv`, raw datasets) and project configuration (`config.yaml`).
- **Autonomous agents** - FastAPI command and analysis service (`run_api.bat` on `http://127.0.0.1:8001` with `/health`, `/analyze`, `/image-info`, `/poll`, `/markers`, and `/markers/reset`) and mock bridge (`mock_unreal_bridge.py` on `http://127.0.0.1:8002`) driving `rodeos_landmark_loop` and `test_marker_step.py`.
- **Open interfaces for research equipment and software** - ZED stereo depth camera telemetry and Unreal Engine polling bridges.

## Environment & Setup Tutorial

### 1. Prerequisites

- Windows 10/11 with an NVIDIA GPU and up-to-date Windows NVIDIA drivers.
- Anaconda or Miniconda installed (and WSL2 + Ubuntu if using legacy TensorFlow/AMBER workflows).
- Git for Windows (with Git LFS for large 3D assets).
- Unreal Engine 5.9 installed at `C:\Program Files\Epic Games\UE_5.9` and Visual Studio 2022 (`MSVC` + Windows SDK) for compiling `RodeOSEditor`.

Verify GPU visibility before setting up ML packages:

```bat
nvidia-smi
```

### 2. Create and Verify the `rodeos-analysis` Conda Environment

Run the following in **Anaconda Prompt** (skip `conda create` if `rodeos-analysis` already exists):

```bat
conda create -n rodeos-analysis python=3.10.22 -y
conda activate rodeos-analysis
python --version
```

Install CUDA-enabled PyTorch (`2.5.1+cu121`), DeepLabCut (`3.0.2`), and the FastAPI/Uvicorn service dependencies:

```bat
pip install torch==2.5.1 torchvision --index-url [https://download.pytorch.org/whl/cu121](https://download.pytorch.org/whl/cu121)
pip install deeplabcut==3.0.2
pip install fastapi uvicorn
```

Verify imports and GPU availability:

```bat
python -c "import torch, deeplabcut, fastapi, uvicorn, pydantic, numpy, PIL; print('PyTorch:', torch.__version__); print('DeepLabCut:', deeplabcut.__version__); print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Not detected'); print('All imports successful')"
```

### 3. Optional Isolated Environments (`sleap` and WSL2 `amber`)

Keep conflicting stacks in separate environments rather than mixing them into `rodeos-analysis`:

- **SLEAP (`sleap`)** - Python `3.11.18`, `numpy==1.26.4`, `pyside6==6.6.1`, `sleap==1.6.6` with Windows Qt/DLL activation and deactivation hooks under `etc\conda\activate.d` and `etc\conda\deactivate.d`.
- **Legacy TensorFlow / AMBER (`amber` in WSL2 Ubuntu)** - Python `3.10`, `deeplabcut==2.3.0`, `tensorflow==2.15.1`, `tf-keras==2.15.0`, `numpy==1.26.4`, `opencv-python==4.11.0.86` with process-local `tf_keras.legacy_tf_layers` aliasing when running legacy TF models.

### 4. Clone and Build `RodeOSsim` for Unreal Engine 5.9

Ensure `RodeOS.uproject` uses `"EngineAssociation": "5.9"` and `Source/RodeOS.Target.cs` + `Source/RodeOSEditor.Target.cs` target `BuildSettingsVersion.V8` (`IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_9` where applicable).

If upgrading from a prior build or engine version, close `UnrealEditor.exe` and `UnrealBuildTool.exe`, clear stale `Binaries` and `Intermediate` folders, compile `RodeOSEditor`, and launch `RodeOS.uproject`:

```bat
taskkill /f /im UnrealEditor.exe 2>nul
taskkill /f /im UnrealBuildTool.exe 2>nul
rmdir /s /q "C:\Users\zaukt\Projects\RodeOSsim\Binaries" 2>nul
rmdir /s /q "C:\Users\zaukt\Projects\RodeOSsim\Intermediate" 2>nul
rmdir /s /q "C:\Users\zaukt\Projects\RodeOSsim\Plugins\RodeOSDLC_plugin\Binaries" 2>nul
rmdir /s /q "C:\Users\zaukt\Projects\RodeOSsim\Plugins\RodeOSDLC_plugin\Intermediate" 2>nul
"C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe" RodeOSEditor Win64 Development -Project="C:\Users\zaukt\Projects\RodeOSsim\RodeOS.uproject" -WaitMutex -FromMsBuild
start "" "C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\Win64\UnrealEditor.exe" "C:\Users\zaukt\Projects\RodeOSsim\RodeOS.uproject"
```

### 5. Run the Landmark Loop, Bridge, and Live PIE Test

1. Start the mock Unreal bridge on port `8002` in an Anaconda Prompt (`rodeos-analysis`):

```bat
cd /d C:\Users\zaukt\Projects\rodeos\src\rodeos_landmark_loop
python mock_unreal_bridge.py
```

2. Start the FastAPI command/analysis server on port `8001` (`run_api.bat`), then reset both services to baseline:

```bat
curl -s -X POST [http://127.0.0.1:8001/markers/reset](http://127.0.0.1:8001/markers/reset)
curl -s -X POST [http://127.0.0.1:8002/reset](http://127.0.0.1:8002/reset)
curl -s [http://127.0.0.1:8001/markers](http://127.0.0.1:8001/markers)
curl -s [http://127.0.0.1:8001/poll](http://127.0.0.1:8001/poll)
```

3. In Unreal Editor 5.9, verify `ARatLandmarkTracker` has `bEnableAgentPolling` enabled and `CommandServerBaseUrl` set to `http://127.0.0.1:8001`, open **Window -> Output Log** filtered to `RAT TRACKER`, and start **Play (PIE)**.

4. Run a step test and inspect `/poll`:

```bat
cd /d C:\Users\zaukt\Projects\rodeos\src\rodeos_landmark_loop
python test_marker_step.py
curl -s [http://127.0.0.1:8001/poll](http://127.0.0.1:8001/poll)
```

## Open Source

RodeOS is being developed as an open-source infrastructure for the biological research community. We welcome researchers, developers, equipment vendors, and academic institutions to contribute.

## Project Status

Early development - architecture, DeepLabCut integration, Unreal Engine 5.9 simulation build, and live marker polling proof-of-concept phase.

**RodeOS Foundation** - Building the infrastructure for reproducible biological simulation.
