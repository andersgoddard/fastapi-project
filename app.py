from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from address_match import score_address_pairs

app = FastAPI(
    title="Address Matching API",
    version="1.0.0"
)

# ---- Request / Response models ----

class AddressPair(BaseModel):
    address1: str
    address2: str


class ScoreRequest(BaseModel):
    pairs: List[AddressPair]


class ScoreResult(BaseModel):
    address1: str
    address2: str
    similarity: float


class ScoreResponse(BaseModel):
    results: List[ScoreResult]


# ---- API endpoint ----

@app.post("/score", response_model=ScoreResponse)
def score_addresses(payload: ScoreRequest):
    results = score_address_pairs(
        [pair.dict() for pair in payload.pairs]
    )
    return {"results": results}
