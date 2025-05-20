# graph_utils.py
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from image_groq_tools import generate_html, evaluate_html, check_feedback

class State(TypedDict):
    sketch: str
    prompt: str
    html: str
    feedback: str
    attempts: int

def build_graph():
    graph = StateGraph(State)
    graph.add_node("generate_html", generate_html)
    graph.add_node("evaluate_html", evaluate_html)

    graph.add_edge(START, "generate_html")
    graph.add_edge("generate_html", "evaluate_html")
    graph.add_conditional_edges(
        "evaluate_html",
        check_feedback,
        {
            "approved": END,
            "retry": "generate_html"
        }
    )

    return graph.compile()
