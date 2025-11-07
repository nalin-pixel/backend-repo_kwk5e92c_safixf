import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Diver, Swipe, Match, Message

app = FastAPI(title="DiveBuddy API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class ObjectIdStr(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        try:
            return str(ObjectId(str(v)))
        except Exception:
            raise ValueError("Invalid ObjectId")


class DiverResponse(Diver):
    id: ObjectIdStr


class CreateDiverRequest(Diver):
    pass


class SwipeRequest(Swipe):
    pass


class MatchResponse(Match):
    id: ObjectIdStr


class MessageResponse(Message):
    id: ObjectIdStr


@app.get("/")
def root():
    return {"message": "DiveBuddy backend running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:60]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:60]}"

    return response


# Diver Endpoints
@app.post("/divers", response_model=dict)
def create_diver(payload: CreateDiverRequest):
    diver_id = create_document("diver", payload)
    return {"id": diver_id}


@app.get("/divers", response_model=List[DiverResponse])
def list_divers(location: Optional[str] = None, level: Optional[str] = None, limit: int = 20):
    filter_dict = {}
    if location:
        filter_dict["location"] = {"$regex": location, "$options": "i"}
    if level:
        filter_dict["level"] = level

    docs = get_documents("diver", filter_dict, limit=limit)
    result: List[DiverResponse] = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        result.append(DiverResponse(**d))
    return result


# Swipe & Match Logic
@app.post("/swipes", response_model=dict)
def record_swipe(payload: SwipeRequest):
    # Save the swipe
    create_document("swipe", payload)

    # If right swipe, check for mutual and create match
    if payload.direction == "right":
        existing = db["swipe"].find_one({
            "swiper_id": payload.target_id,
            "target_id": payload.swiper_id,
            "direction": "right",
        })
        if existing:
            # Create match document (order user ids for idempotency)
            a, b = sorted([payload.swiper_id, payload.target_id])
            already = db["match"].find_one({"user_a_id": a, "user_b_id": b})
            if not already:
                match_id = create_document("match", Match(user_a_id=a, user_b_id=b))
                return {"matched": True, "match_id": match_id}
            else:
                return {"matched": True, "match_id": str(already["_id"]) }

    return {"matched": False}


# Messaging
class CreateMessageRequest(BaseModel):
    match_id: str
    sender_id: str
    content: str


@app.post("/messages", response_model=dict)
def send_message(payload: CreateMessageRequest):
    # Ensure match exists
    m = db["match"].find_one({"_id": ObjectId(payload.match_id)})
    if not m:
        raise HTTPException(status_code=404, detail="Match not found")

    msg_id = create_document("message", Message(**payload.model_dump()))
    # Update match preview
    db["match"].update_one({"_id": ObjectId(payload.match_id)}, {"$set": {"last_message_preview": payload.content}})
    return {"id": msg_id}


@app.get("/messages/{match_id}", response_model=List[MessageResponse])
def get_messages(match_id: str, limit: int = 50):
    docs = get_documents("message", {"match_id": match_id}, limit=limit)
    result: List[MessageResponse] = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        result.append(MessageResponse(**d))
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
