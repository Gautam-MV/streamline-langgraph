import streamlit as st
from PIL import Image
import tempfile
import os
import subprocess
import socket
import time
import psutil
from graph_utils import build_graph, State
from ui_renderer import save_and_preview_generated_ui
from streamlit_drawable_canvas import st_canvas
import numpy as np
from image_groq_tools import set_groq_api_key

st.set_page_config(page_title="Sketch to UI", layout="wide")
st.title("🖌️ Sketch to Functional UI Generator")

# Function to stop a process on a given port
def stop_process_on_port(port):
    """
    Automatically stop any process running on the given port.
    """
    process_stopped = False
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    st.info(f"Found process {conn.pid} using port {port}. Attempting to terminate...")
                    proc.terminate()  # Gracefully terminate
                    proc.wait(timeout=5)
                    st.success(f"Successfully terminated process {conn.pid} on port {port}.")
                    process_stopped = True
                except psutil.AccessDenied:
                    st.error(f"Access denied while trying to terminate process {conn.pid}. Please run with elevated permissions.")
                except psutil.NoSuchProcess:
                    st.warning(f"Process {conn.pid} no longer exists.")
                except psutil.TimeoutExpired:
                    st.error(f"Timeout while stopping process {conn.pid}. Trying to kill the process...")
                    proc.kill()  # Force kill
                    st.success(f"Forcefully killed process {conn.pid}.")
                    process_stopped = True
                except Exception as e:
                    st.error(f"Unexpected error stopping process {conn.pid} on port {port}: {e}")
    except Exception as e:
        st.error(f"Error accessing port {port}: {e}")
    return process_stopped

# Function to clear the `ui_output` folder
def clear_ui_output(output_dir):
    """
    Clears all files in the `ui_output` directory except `app.py`.
    """
    try:
        for filename in os.listdir(output_dir):
            if filename != "app.py":
                file_path = os.path.join(output_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        st.success(f"Cleared all files in '{output_dir}' except 'app.py'.")
    except Exception as e:
        st.error(f"Error clearing 'ui_output': {e}")

# Layout: Two columns
col1, col2 = st.columns([1, 2])  # Left: Settings | Right: Canvas

with col1:
    st.subheader("📤 Upload or Configure Drawing")
    sketch_file = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])

    st.markdown("### ✏️ Drawing Options")
    drawing_mode = st.selectbox("Drawing mode", ("freedraw", "line", "rect", "circle", "transform"))
    stroke_width = st.slider("Stroke width", 1, 10, 3)
    stroke_color = st.color_picker("Stroke color", "#000000")
    hex_fill = st.color_picker("Fill color", "#FFA500")
    fill_alpha = st.slider("Fill Transparency (0 = transparent, 1 = opaque)", 0.0, 1.0, 0.3)

    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    r, g, b = hex_to_rgb(hex_fill)
    fill_color = f"rgba({r}, {g}, {b}, {fill_alpha})"

    st.markdown("### 💬 Prompt for UI Generation")
    prompt = st.text_area(
        "Describe what the UI should include",
        value="Generate accurate dashboard HTML/CSS/JS from this sketch. The CSS HTML styles should be very beautiful..enhance the visual representation"
    )

    st.markdown("### 🔑 Enter Groq API Key")
    groq_api_key = st.text_input("Groq API Key", type="password")
    set_api_clicked = st.button("🔐 Set API Key")

    if set_api_clicked:
        if groq_api_key:
            set_groq_api_key(groq_api_key)
            st.success("Groq API Key set successfully!")
        else:
            st.error("Please enter a valid API Key.")

    generate_clicked = st.button("🚀 Generate UI")

with col2:
    st.subheader("🖍️ Draw UI Sketch")
    canvas_result = st_canvas(
        fill_color=fill_color,
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color="#FFFFFF",
        height=500,
        width=700,
        drawing_mode=drawing_mode,
        key="canvas",
    )

# If Generate Button Clicked
if generate_clicked and (sketch_file or (canvas_result.image_data is not None)):
    with st.spinner("Generating HTML..."):
        # Save sketch
        if sketch_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(sketch_file.read())
                sketch_path = tmp.name
        else:
            image = Image.fromarray((canvas_result.image_data[:, :, :3]).astype(np.uint8))
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                image.save(tmp.name)
                sketch_path = tmp.name

        # Build LangGraph flow
        flow = build_graph()
        state: State = {
            "sketch": sketch_path,
            "prompt": prompt,
            "html": "",
            "feedback": "",
            "attempts": 0
        }
        final_state = flow.invoke(state)

        st.subheader("✅ Feedback")
        st.markdown(final_state["feedback"])

        # Clear `ui_output` folder
        ui_dir = "ui_output"
        clear_ui_output(ui_dir)

        # Save and preview generated HTML/CSS/JS
        save_and_preview_generated_ui(final_state["html"])

        # Stop existing process on port 8502
        stop_process_on_port(8502)

        # Launch subprocess to run app.py in a new Streamlit session
        try:
            subprocess.Popen(["streamlit", "run", "app.py", "--server.port", "8502"], cwd=ui_dir)
            st.success("🎉 UI launched in a new tab.")
            st.markdown("👉 [Open Generated UI](http://localhost:8502)", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Failed to launch UI: {e}")
