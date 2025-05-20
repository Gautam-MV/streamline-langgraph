import base64
from groq import Groq
from typing import TypedDict

groq_api_key = None  # Global variable for API Key
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

class State(TypedDict):
    sketch: str
    prompt: str
    html: str
    feedback: str
    attempts: int

def set_groq_api_key(key: str):
    """Set the Groq API Key globally."""
    global groq_api_key
    groq_api_key = key

def image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def generate_html(state: State) -> dict:
    print("GENERATE_HTML CALLED")
    if not groq_api_key:
        raise ValueError("Groq API Key not set. Please set it before generating HTML.")
    
    b64_img = image_to_base64(state["sketch"])
    feedback = state.get("feedback", "")
    full_prompt = f"{state['prompt']}\n{'Previous feedback: ' + feedback if feedback and 'APPROVED' not in feedback.upper() else ''}"

    client = Groq(api_key=groq_api_key)
    res = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": full_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
            ]
        }]
    )
    state["html"] = res.choices[0].message.content.strip()
    return state

def evaluate_html(state: State) -> dict:
    print("EVALUATE_HTML CALLED", state["attempts"])
    if not groq_api_key:
        raise ValueError("Groq API Key not set. Please set it before evaluating HTML.")

    b64_img = image_to_base64(state["sketch"])
    prompt = f"""
    You are a UI evaluator. Compare the HTML/CSS/JS to the original sketch.
    If it fully matches, reply only word "**APPROVED**". If you are not fully satisfied, any tinniest discrepancies, include word "**NOT APPROVED**".
    HTML: {state['html']}
    """

    client = Groq(api_key=groq_api_key)
    res = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
            ]
        }]
    )

    try:
        feedback = res.choices[0].message.content.strip()
    except Exception as e:
        feedback = f"Error: {e}"
    state["feedback"] = feedback
    if "**APPROVED**" not in feedback.upper():
        state["attempts"] += 1
    return state


def check_feedback(state: State) -> str:
    if state["attempts"] >= 8:
        state["feedback"] += "\nToo many retries. Exiting."
        return "approved"
    elif "**APPROVED**" not in state["feedback"].upper():
        return "retry"
    else:
        return "approved"
