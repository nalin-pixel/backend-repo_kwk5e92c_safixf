"""
Database Schemas for DiveBuddy

Each Pydantic model represents a collection in MongoDB. The collection
name is the lowercase of the class name (e.g., Diver -> "diver").
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl


class Diver(BaseModel):
    """
    Divers collection schema
    Collection: "diver"
    """
    name: str = Field(..., description="Display name")
    location: str = Field(..., description="Primary dive location")
    level: Literal[
        "Open Water",
        "Advanced Open Water",
        "Rescue Diver",
        "Divemaster",
        "Instructor",
    ] = Field(..., description="Certification level")
    experience: int = Field(0, ge=0, description="Logged dives count")
    bio: Optional[str] = Field(None, description="Short bio")
    image: Optional[HttpUrl] = Field(None, description="Profile image URL")
    interests: List[str] = Field(default_factory=list, description="Dive interests/tags")
    availability: Optional[str] = Field(None, description="Dates or range (free text)")


class Swipe(BaseModel):
    """
    Swipes collection schema
    Collection: "swipe"
    """
    swiper_id: str = Field(..., description="User (diver) who performed the swipe")
    target_id: str = Field(..., description="User (diver) who was swiped on")
    direction: Literal["left", "right"] = Field(..., description="Swipe direction")


class Match(BaseModel):
    """
    Matches collection schema
    Collection: "match"
    """
    user_a_id: str = Field(..., description="First user id")
    user_b_id: str = Field(..., description="Second user id")
    last_message_preview: Optional[str] = Field(None, description="Preview of last message")


class Message(BaseModel):
    """
    Messages collection schema
    Collection: "message"
    """
    match_id: str = Field(..., description="Related match id")
    sender_id: str = Field(..., description="User who sent the message")
    content: str = Field(..., description="Message text content")
