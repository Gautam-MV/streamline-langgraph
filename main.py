import streamlit as st
from PIL import Image
import tempfile
import os
import subprocess
import signal
import socket
import time
from graph_utils import build_graph, State
from ui_preview import save_and_preview_generated_ui
from streamlit_drawable_canvas import st_canvas
import numpy as np
from image_groq_tools import set_groq_api_key

st.set_page_config(page_title="Sketch to UI", layout="wide")
st.title("🖌️ Sketch to Functional UI Generator")

# Initialize process state
if "ui_process" not in st.session_state:
    st.session_state.ui_process = None

def kill_process(proc):
    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    except Exception as e:
        st.error(f"Error killing process: {e}")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

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

        # Save and preview generated HTML/CSS/JS
        save_and_preview_generated_ui(final_state["html"])

        # Launch subprocess to run app.py
        ui_dir = "ui_output"

        # Stop previous process if running
        if st.session_state.ui_process:
            st.info("Stopping previous UI server...")
            kill_process(st.session_state.ui_process)
            st.session_state.ui_process = None
            time.sleep(1)

        if is_port_in_use(8000):
            st.error("Port 8000 is in use. Please stop the UI server or restart Streamlit.")
        else:
            st.session_state.ui_process = subprocess.Popen(["python", "app.py"], cwd=ui_dir)
            st.success("🎉 UI launched in a new tab.")
            st.markdown("👉 [Open UI](http://localhost:8000)", unsafe_allow_html=True)
