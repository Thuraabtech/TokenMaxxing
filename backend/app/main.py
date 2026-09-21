from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import cost_tracker
from app.pipeline.graph import run
from app.schemas import ChatRequest, ChatResponse

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="TokenMaxxer")


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    state = run(request.message)
    results = state["results"]
    total_cost = sum(r.cost_usd for r in results) + state["overhead_cost_usd"]
    total_saved = sum(r.saved_usd for r in results) + state["overhead_saved_usd"]
    snapshot = cost_tracker.snapshot()

    return ChatResponse(
        answer=state["final_answer"],
        subtasks=results,
        total_cost_usd=round(total_cost, 6),
        total_saved_usd=round(total_saved, 6),
        running_total_usd=snapshot["running_total_usd"],
        running_saved_usd=snapshot["running_saved_usd"],
        retrieved_sources=sorted({r["source"] for r in state["retrieved"]}),
    )


@app.get("/api/cost-summary")
def cost_summary() -> dict:
    return cost_tracker.snapshot()


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
