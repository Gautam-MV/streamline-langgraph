import streamlit as st
import os
import re

st.set_page_config(page_title="Generated UI Preview", layout="wide")

OUTPUT_DIR = "."  # adjust if needed
html_file = os.path.join(OUTPUT_DIR, "index.html")

st.title("🎨 Generated UI Preview")

if os.path.exists(html_file):
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Find all CSS and JS file references and inline their content
    # Inline CSS
    css_files = re.findall(r'<link rel="stylesheet" href="([^"]+\.css)"', html_content)
    for css_file in css_files:
        css_path = os.path.join(OUTPUT_DIR, css_file)
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as css_f:
                css_content = css_f.read()
            style_tag = f"<style>\n{css_content}\n</style>"
            # Replace the link tag with the style tag
            html_content = re.sub(f'<link rel="stylesheet" href="{css_file}">', style_tag, html_content)

    # Inline JS
    js_files = re.findall(r'<script src="([^"]+\.js)"></script>', html_content)
    for js_file in js_files:
        js_path = os.path.join(OUTPUT_DIR, js_file)
        if os.path.exists(js_path):
            with open(js_path, "r", encoding="utf-8") as js_f:
                js_content = js_f.read()
            script_tag = f"<script>\n{js_content}\n</script>"
            # Replace the script tag with inline script
            html_content = re.sub(f'<script src="{js_file}"></script>', script_tag, html_content)

    st.components.v1.html(html_content, height=800, scrolling=True)
else:
    st.warning("No generated UI found. Please generate UI first.")
