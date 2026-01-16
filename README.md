# LiveCAD: Parametric Engineering & Live-Coding Tool

**LiveCAD** is a standalone Python environment designed for "Code-CAD" workflows. It allows you to generate high-precision, parametric 3D geometry using Python scripts, with real-time visualization and dynamic slider adjustment.

Unlike standard boolean-based CAD, LiveCAD utilizes mathematical mesh construction (via `numpy` meshgrids) to generate high-fidelity features like screw threads, helical gears, and organic textures that are fully watertight and 3D print ready.

## 🚀 Features

* **Real-Time Parametric Design:** The tool automatically parses your code for a `parameters` dictionary and generates GUI sliders instantly.
* **High-Fidelity Threading:** Includes logic for mathematically generating ISO metric threads without computationally expensive boolean operations.
* **AI-Ready Workflow:** Includes a `GEM_INSTRUCTIONS.txt` system prompt to train your own LLM (Gemini, ChatGPT, Claude) to become a dedicated "LiveCAD Engineer."
* **Local & Secure:** Runs entirely offline. No cloud dependencies, no API keys required within the app.
* **Robust Dependencies:** Pre-configured with `mapbox_earcut` and `shapely` for complex 2D-to-3D extrusions (Torx heads, gears, brackets).
* **Direct STL Export:** One-click export to STL for slicers (Orca, Cura, PrusaSlicer).

## 🛠️ Installation

### Prerequisites
* Windows 10/11
* Python 3.10+ installed and added to PATH.

### Quick Start
1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/YourUsername/LiveCAD.git](https://github.com/YourUsername/LiveCAD.git)
    cd LiveCAD
    ```
2.  **Initialize Environment:**
    Double-click `setup.bat`.
    * *This creates a local `venv` and installs all heavy dependencies (Trimesh, PyVistaQt, PyQt6).*
3.  **Launch:**
    Double-click `run.bat`.

## 📖 Usage Guide

### 1. The Interface
* **Left Panel (Code Editor):** Write your Python generation script here.
* **Top Left (Dynamic Parameters):** Sliders appear here automatically based on your code.
* **Bottom Left (Mesh Offset):** A global tolerance adjuster. Set to `-0.1mm` for tighter fits or `+0.2mm` for clearance without changing the code.
* **Right Panel (Viewer):** Interactive 3D view. Left-click to rotate, Right-click to pan, Scroll to zoom.

### 2. Writing a Script
Your script must follow this specific structure to work with the engine:

```python
import trimesh
import numpy as np

# [1] DEFINE PARAMETERS
# Format: 'Name': (Default, Min, Max)
parameters = {
    'radius': (10.0, 1.0, 50.0),
    'height': (20.0, 1.0, 100.0)
}

# [2] DEFINE GENERATOR
def generate(params):
    # Imports must be inside the function for local execution scope
    from shapely.geometry import Polygon
    
    r = params['radius']
    h = params['height']
    
    # Create Geometry
    mesh = trimesh.creation.cylinder(radius=r, height=h)
    
    return mesh
