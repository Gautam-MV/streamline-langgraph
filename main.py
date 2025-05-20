import streamlit as st
from PIL import Image
import tempfile
import os
import subprocess
import time
import socket
import webbrowser
import numpy as np
from streamlit_drawable_canvas import st_canvas

from graph_utils import build_graph, State
from ui_preview import save_and_preview_generated_ui
from image_groq_tools import set_groq_api_key

st.set_page_config(page_title="Sketch to UI", layout="wide")
st.title("🖌️ Sketch to Functional UI Generator")

# Initialize process state for preview UI app
if "preview_process" not in st.session_state:
    st.session_state.preview_process = None

def kill_process(proc):
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

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

if generate_clicked and (sketch_file or (canvas_result.image_data is not None)):
    with st.spinner("Generating HTML..."):
        # Save sketch image file
        if sketch_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(sketch_file.read())
                sketch_path = tmp.name
        else:
            image = Image.fromarray((canvas_result.image_data[:, :, :3]).astype(np.uint8))
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                image.save(tmp.name)
                sketch_path = tmp.name

        # Build LangGraph flow and run it
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

        # Save generated HTML/CSS/JS to ui_output folder
        save_and_preview_generated_ui(final_state["html"])

        # Launch preview app.py as a new Streamlit app on port 8502
        PREVIEW_PORT = 8502
        preview_url = f"http://localhost:{PREVIEW_PORT}"

        # Kill any existing preview process
        if st.session_state.preview_process:
            st.info("Stopping previous preview server...")
            kill_process(st.session_state.preview_process)
            st.session_state.preview_process = None
            time.sleep(1)

        if is_port_in_use(PREVIEW_PORT):
            st.error(f"Port {PREVIEW_PORT} is already in use. Please free it and try again.")
        else:
            # Launch preview app.py subprocess
            st.session_state.preview_process = subprocess.Popen(
                ["streamlit", "run", "app.py", "--server.port", str(PREVIEW_PORT)],
                cwd="ui_output",  # Run from ui_output folder if app.py is there, else adjust path
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for server to start
            time.sleep(3)

            st.success("🎉 Preview UI launched!")

            # Open preview in new browser tab automatically
            webbrowser.open_new_tab(preview_url)

            # Also show clickable link
            st.markdown(f"### 👉 [Open Generated UI Preview]({preview_url})", unsafe_allow_html=True)
