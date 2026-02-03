from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from address_match import score_address_pairs
from mangum import Mangum

app = FastAPI()

class AddressPair(BaseModel):
    address1: str
    address2: str

class MatchResult(BaseModel):
    address1: str
    address2: str
    similarity: float

class MatchRequest(BaseModel):
    pairs: List[AddressPair]

class MatchResponse(BaseModel):
    results: List[MatchResult]
    
@app.post("/match", response_model=MatchResponse)
def match(req: MatchRequest):
    results = score_address_pairs([p.dict() for p in req.pairs])
    return {"results": results}
    
handler = Mangum(app)