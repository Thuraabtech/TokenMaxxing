"""Linear LangGraph pipeline: retrieve -> segment -> route each sub-task -> assemble.

The blueprint's diagram shows escalation as a loop back to a higher tier --
here that loop is implemented inside router.route() as a bounded retry
(see settings.max_escalations) rather than as a graph cycle. A 2-hop bounded
escalation doesn't need general graph cycles; if routing logic grows more
elaborate later (e.g. per-tier fallback strategies), promote it to real
conditional edges then.
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app import cost_tracker
from app.pipeline import assembler, retriever, router, segmenter
from app.schemas import SubtaskResult


class PipelineState(TypedDict):
    message: str
    retrieved: list[dict]
    subtasks: list[dict]
    results: list[SubtaskResult]
    final_answer: str
    overhead_cost_usd: float
    overhead_saved_usd: float


def _retrieve_node(state: PipelineState) -> dict:
    try:
        retrieved = retriever.retrieve(state["message"])
    except FileNotFoundError:
        # No index built yet -- degrade to no-RAG rather than failing the request.
        retrieved = []
    return {"retrieved": retrieved}


def _segment_node(state: PipelineState) -> dict:
    subtasks, in_tok, out_tok = segmenter.segment(state["message"])
    cost, saved = cost_tracker.record("low", in_tok, out_tok)
    return {"subtasks": subtasks, "overhead_cost_usd": cost, "overhead_saved_usd": saved}


def _route_node(state: PipelineState) -> dict:
    results = [
        router.route(subtask, state["retrieved"] if subtask.get("needs_retrieval") else [])
        for subtask in state["subtasks"]
    ]
    return {"results": results}


def _assemble_node(state: PipelineState) -> dict:
    answer, cost, saved = assembler.assemble(state["message"], state["results"])
    return {
        "final_answer": answer,
        "overhead_cost_usd": state["overhead_cost_usd"] + cost,
        "overhead_saved_usd": state["overhead_saved_usd"] + saved,
    }


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("retrieve", _retrieve_node)
    graph.add_node("segment", _segment_node)
    graph.add_node("route", _route_node)
    graph.add_node("assemble", _assemble_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "segment")
    graph.add_edge("segment", "route")
    graph.add_edge("route", "assemble")
    graph.add_edge("assemble", END)

    return graph.compile()


_compiled_graph = None


def run(message: str) -> PipelineState:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph.invoke(
        {
            "message": message,
            "retrieved": [],
            "subtasks": [],
            "results": [],
            "final_answer": "",
            "overhead_cost_usd": 0.0,
            "overhead_saved_usd": 0.0,
        }
    )
