# ui_preview.py

import re
import os
import http.server
import socketserver
import webbrowser
from typing import Tuple

def parse_markdown_generated_code(content: str) -> Tuple[str, str, str]:
    html_match = re.search(r"```html\n(.*?)```", content, re.DOTALL)
    css_match = re.search(r"```css\n(.*?)```", content, re.DOTALL)
    js_match = re.search(r"```javascript\n(.*?)```", content, re.DOTALL)
    return (
        html_match.group(1).strip() if html_match else "",
        css_match.group(1).strip() if css_match else "",
        js_match.group(1).strip() if js_match else "",
    )

def save_code_files(html: str, css: str, js: str, output_dir: str = "ui_output"):
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "index.html"), "w") as f:
        f.write(html)
    with open(os.path.join(output_dir, "style.css"), "w") as f:
        f.write(css)
    with open(os.path.join(output_dir, "script.js"), "w") as f:
        f.write(js)

    print(f"✅ Code saved to '{output_dir}/'")

def save_and_preview_generated_ui(markdown_output: str):
    html, css, js = parse_markdown_generated_code(markdown_output)
    save_code_files(html, css, js)
