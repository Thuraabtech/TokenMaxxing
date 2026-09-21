# TokenMaxxer

A complexity-routed RAG chatbot: prompts get split into sub-tasks, each
sub-task is scored for difficulty, and only the cheapest Bedrock model tier
that can handle it gets called. See the architecture blueprint for the full
design rationale (classifier approach, why OpenSearch Serverless is out,
where TOON actually helps, budget breakdown).

## Stack

- **Backend**: FastAPI + LangGraph, raw `boto3` Bedrock Converse calls (for
  accurate per-tier token/cost accounting), FAISS for retrieval.
- **Frontend**: a single static page (no build step) — chat on the left, a
  live cost/tier dashboard on the right.
- **Model tiers**: `amazon.nova-micro-v1:0` (low) → Claude Haiku (medium) →
  Claude Sonnet (high), all via Bedrock.

## One-time AWS setup

1. In the Bedrock console, request model access for Amazon Nova Micro and
   whichever Claude models you plan to use for the medium/high tiers.
   Access requests are usually approved instantly but aren't automatic.
2. Configure credentials locally (`aws configure`, or `AWS_ACCESS_KEY_ID` /
   `AWS_SECRET_ACCESS_KEY` env vars) for an IAM identity with
   `bedrock:InvokeModel`, `bedrock:Converse`, and embedding-model access.
3. Look up the exact current Bedrock model IDs for your Claude tiers —
   these strings change as new versions ship, so don't hardcode a guess:
   ```
   aws bedrock list-foundation-models --by-provider anthropic --query "modelSummaries[].modelId" --region us-east-1
   ```
4. **Set AWS Budget alerts (e.g. $20 / $50 / $80) before running any real
   traffic.** A routing bug that sends everything to the high tier can burn
   a $100 credit in hours.

## Local setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt

cp ../.env.example ../.env    # then fill in MODEL_ID_MEDIUM / MODEL_ID_HIGH from step 3 above

python -m app.data.ingest     # builds the FAISS index from app/data/sample_docs
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000` — FastAPI serves the frontend directly.

## Running tests

The classifier and TOON codec tests don't touch AWS and run with plain pytest:

```bash
cd backend
pytest
```

Anything exercising `bedrock_client`, `retriever`, `segmenter`, `router`, or
`assembler` needs real AWS credentials and Bedrock model access, so those
aren't covered by automated tests here — test them by actually running the
app.

## Where the placeholders are

- **`app/pipeline/classifier.py`** is a heuristic (keyword + length) tier
  classifier — a stand-in for the trained embedding classifier described in
  the blueprint. It exists so the pipeline is runnable end-to-end from day
  one. To replace it: log real routing decisions and outcomes (the app
  already runs every sub-task through `cost_tracker`), hand-label ~300-500
  of them, train a small classifier on their embeddings, and swap the body
  of `classify()` — `router.py` doesn't need to change.
- **`app/data/sample_docs/`** has three short docs about the research this
  project is built on (FrugalGPT, RouteLLM, TOON), so there's something to
  retrieve out of the box. Replace with your own corpus and re-run
  `python -m app.data.ingest`.
- **`.env.example`** ships with real pricing figures as of when this was
  written — re-check `aws bedrock` pricing before trusting the dashboard's
  dollar figures for anything beyond relative tier comparison.

## Project layout

```
backend/
  app/
    main.py            FastAPI app (chat endpoint + static file serving)
    config.py           settings (model ids, thresholds, pricing)
    bedrock_client.py    boto3 Converse API wrapper
    toon_codec.py        hand-rolled TOON encode/decode (uniform tables only)
    cost_tracker.py      in-memory running cost ledger
    pipeline/
      retriever.py        FAISS + Bedrock embeddings
      segmenter.py         splits a prompt into sub-tasks (low-tier model)
      classifier.py         heuristic tier classifier (see placeholders above)
      router.py             calls the right tier, handles confidence-based escalation
      assembler.py           merges sub-task answers into one reply
      graph.py               wires the above into a LangGraph pipeline
    data/
      sample_docs/          seed corpus
      ingest.py              builds the FAISS index
  tests/                   classifier + TOON codec unit tests (no AWS needed)
  frontend/
    index.html, app.js, styles.css   chat UI + cost/tier dashboard, no build step
```

`frontend/` lives inside `backend/` (rather than as a sibling) so that
deploy targets that isolate `backend/` as the build root — e.g. Railway
with a Root Directory setting — still include it.

