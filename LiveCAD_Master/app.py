import sys
import numpy as np
import trimesh
import pyvista as pv
from PyQt6 import QtWidgets, QtCore, QtGui
from pyvistaqt import QtInteractor

DEFAULT_CODE = """import trimesh
import numpy as np

# [PARAMETERS]
parameters = {
    'diameter_m': (10.0, 3.0, 30.0),    # Major diameter (e.g., M10)
    'length': (40.0, 10.0, 150.0),      # Thread length
    'pitch': (1.5, 0.5, 4.0),           # Thread pitch
    'head_size': (17.0, 5.0, 50.0),     # Hex width across flats
    'head_height': (7.0, 2.0, 20.0),    # Thickness of the head
    'resolution': (64, 32, 128)         # Radial segments
}

def generate(params):
    # --- Unpack Parameters ---
    d_major = params['diameter_m']
    length = params['length']
    pitch = params['pitch']
    hex_flats = params['head_size']
    head_h = params['head_height']
    res = int(params['resolution'])
    
    # --- Derived Dimensions ---
    # Hexagon radius (center to corner) = flats / sqrt(3)
    head_radius = hex_flats / np.sqrt(3)
    
    # ISO Thread Depth Approximation
    thread_depth = 0.613 * pitch 
    d_minor = d_major - (2 * thread_depth)
    
    # --- 1. Generate The Hex Head ---
    head = trimesh.creation.cylinder(
        radius=head_radius, 
        height=head_h, 
        sections=6
    )
    # Rotate so flats align with axes
    head.apply_transform(trimesh.transformations.rotation_matrix(np.radians(30), [0, 0, 1]))
    # Move head to the top (Z = length)
    # Cylinder is centered at 0, so move up by length + half height
    head.apply_translation([0, 0, length + head_h/2])

    # --- 2. Generate Threaded Shaft (Mathematical Construction) ---
    # We build the mesh manually to control the spiral V-shape
    
    # Vertical resolution: we need enough slices to form the V-shape of the thread
    slices_per_pitch = 12
    total_slices = int((length / pitch) * slices_per_pitch)
    if total_slices < 2: total_slices = 2
    
    # Create Grid
    theta = np.linspace(0, 2*np.pi, res, endpoint=False)
    z_vals = np.linspace(0, length, total_slices)
    theta_grid, z_grid = np.meshgrid(theta, z_vals)
    
    # Calculate Thread Profile (Triangle Wave)
    # 1. Normalize angle and Z to find phase
    angle_norm = theta_grid / (2*np.pi)
    z_pitch_norm = z_grid / pitch
    
    # 2. Helix Phase (0.0 to 1.0)
    helix_phase = (z_pitch_norm - angle_norm) % 1.0
    
    # 3. Triangle Wave: 0->1->0 based on phase
    profile = 1.0 - 2.0 * np.abs(helix_phase - 0.5)
    
    # 4. Taper logic (fade out threads at the bottom tip)
    taper_len = 1.5 * pitch
    taper_mask = np.clip(z_grid / taper_len, 0.0, 1.0) 
    
    # 5. Calculate Radius at every point
    r_base = d_minor / 2.0
    r_offset = thread_depth * profile
    
    # Apply taper to the thread depth and the base cylinder
    current_r = (r_base + r_offset) * np.minimum(1.0, 0.8 + 0.2*taper_mask)
    
    # Convert Cylindrical to Cartesian
    x = current_r * np.cos(theta_grid)
    y = current_r * np.sin(theta_grid)
    z = z_grid
    
    # Stack vertices: (N, 3)
    vertices = np.column_stack((x.flatten(), y.flatten(), z.flatten()))
    
    # --- Generate Faces ---
    rows = total_slices
    cols = res
    idx = np.arange(rows * cols).reshape((rows, cols))
    
    c = idx[:-1, :].flatten()
    cn = np.roll(idx[:-1, :], -1, axis=1).flatten()
    n = idx[1:, :].flatten()
    nn = np.roll(idx[1:, :], -1, axis=1).flatten()
    
    f1 = np.column_stack((c, cn, nn))
    f2 = np.column_stack((c, nn, n))
    faces = np.vstack((f1, f2))
    
    thread_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    
    # --- 3. Cap the bottom ---
    cap = trimesh.creation.cylinder(
        radius=d_minor/2 * 0.8, 
        height=pitch/2, 
        sections=res
    )
    cap.apply_translation([0, 0, pitch/4])
    
    # --- Assembly ---
    bolt = trimesh.util.concatenate([head, thread_mesh, cap])
    
    # Final Orientation: Bottom of Head at Z=0
    bolt.apply_translation([0, 0, -length])
    
    return bolt
"""

class ParamSlider(QtWidgets.QWidget):
    value_changed = QtCore.pyqtSignal(str, float)

    def __init__(self, name, default, min_val, max_val, is_int=False):
        super().__init__()
        self.name = name
        self.is_int = is_int
        self.multiplier = 1 if is_int else 100
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QtWidgets.QLabel(f"{name}:")
        self.label.setFixedWidth(80)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(min_val * self.multiplier))
        self.slider.setMaximum(int(max_val * self.multiplier))
        self.slider.setValue(int(default * self.multiplier))
        self.input = QtWidgets.QDoubleSpinBox()
        self.input.setRange(min_val, max_val)
        self.input.setValue(default)
        self.input.setSingleStep(1 if is_int else 0.1)
        self.input.setDecimals(0 if is_int else 2)
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(self.input)
        self.slider.valueChanged.connect(self._on_slider)
        self.input.valueChanged.connect(self._on_input)

    def _on_slider(self, val):
        float_val = val / self.multiplier
        self.input.blockSignals(True)
        self.input.setValue(float_val)
        self.input.blockSignals(False)
        self.value_changed.emit(self.name, float_val)

    def _on_input(self, val):
        self.slider.blockSignals(True)
        self.slider.setValue(int(val * self.multiplier))
        self.slider.blockSignals(False)
        self.value_changed.emit(self.name, val)

class LiveCADWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LiveCAD: Parametric Engineering Tool")
        self.resize(1600, 900)
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        main_layout.addWidget(left_panel, stretch=1)
        
        self.param_scroll = QtWidgets.QScrollArea()
        self.param_scroll.setWidgetResizable(True)
        self.param_container = QtWidgets.QWidget()
        self.param_layout = QtWidgets.QVBoxLayout(self.param_container)
        self.param_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.param_scroll.setWidget(self.param_container)
        self.param_scroll.setFixedHeight(300)
        left_layout.addWidget(QtWidgets.QLabel("<b>Dynamic Parameters</b>"))
        left_layout.addWidget(self.param_scroll)
        
        offset_group = QtWidgets.QGroupBox("Mesh Offset (mm)")
        offset_layout = QtWidgets.QHBoxLayout(offset_group)
        self.offset_spin = QtWidgets.QDoubleSpinBox()
        self.offset_spin.setRange(-5.0, 5.0)
        self.offset_spin.setSingleStep(0.05)
        self.offset_spin.setValue(0.0)
        self.offset_spin.valueChanged.connect(self.run_generation)
        offset_layout.addWidget(QtWidgets.QLabel("Offset:"))
        offset_layout.addWidget(self.offset_spin)
        left_layout.addWidget(offset_group)

        left_layout.addWidget(QtWidgets.QLabel("<b>Python Code</b>"))
        self.editor = QtWidgets.QTextEdit()
        self.editor.setFont(QtGui.QFont("Consolas", 10))
        self.editor.setPlainText(DEFAULT_CODE)
        self.editor.setLineWrapMode(QtWidgets.QTextEdit.LineWrapMode.NoWrap)
        left_layout.addWidget(self.editor)
        
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Parse Parameters")
        self.btn_refresh.clicked.connect(self.parse_parameters)
        self.btn_export = QtWidgets.QPushButton("Export STL")
        self.btn_export.clicked.connect(self.export_stl)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_export)
        left_layout.addLayout(btn_layout)

        self.plotter = QtInteractor(self)
        self.plotter.set_background("black")
        self.plotter.add_axes()
        self.plotter.show_grid()
        main_layout.addWidget(self.plotter.interactor, stretch=2)

        self.current_params = {}
        self.generated_mesh = None
        self.parse_parameters()

    def parse_parameters(self):
        code = self.editor.toPlainText()
        local_scope = {}
        try:
            exec(code, {}, local_scope)
            if 'parameters' not in local_scope: return
            new_params_def = local_scope['parameters']
            for i in reversed(range(self.param_layout.count())): 
                self.param_layout.itemAt(i).widget().setParent(None)
            self.current_params = {}
            for key, val in new_params_def.items():
                slider = ParamSlider(key, *val, isinstance(val[0], int))
                slider.value_changed.connect(self.update_param_and_run)
                self.param_layout.addWidget(slider)
                self.current_params[key] = val[0]
            self.run_generation()
        except Exception as e: print(f"Error: {e}")

    def update_param_and_run(self, name, value):
        self.current_params[name] = value
        self.run_generation()

    def run_generation(self):
        code = self.editor.toPlainText()
        local_scope = {}
        try:
            exec(code, globals(), local_scope)
            if 'generate' not in local_scope: return
            mesh = local_scope['generate'](self.current_params)
            offset = self.offset_spin.value()
            if abs(offset) > 0.001:
                mesh.fix_normals()
                mesh.vertices += mesh.vertex_normals * offset
            self.generated_mesh = mesh
            self.plotter.clear()
            self.plotter.add_mesh(mesh, color="cyan", show_edges=True, opacity=0.8)
            self.plotter.reset_camera()
        except Exception as e: print(f"Runtime Error: {e}")

    def export_stl(self):
        if self.generated_mesh:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save STL", "", "STL (*.stl)")
            if path: self.generated_mesh.export(path)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LiveCADWindow()
    window.show()
    sys.exit(app.exec())
