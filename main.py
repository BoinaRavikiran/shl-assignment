from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import json

app = FastAPI()

# -----------------------------
# LOAD SHL CATALOG
# -----------------------------
with open("shl_catalog.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

# -----------------------------
# REQUEST SCHEMA
# -----------------------------
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

# -----------------------------
# HEALTH ENDPOINT
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# -----------------------------
# BUILD SEARCHABLE TEXT
# -----------------------------
def build_search_text(item):

    searchable_text = ""

    searchable_text += item.get("name", "") + " "
    searchable_text += item.get("description", "") + " "
    searchable_text += item.get("duration", "") + " "
    searchable_text += item.get("test_type", "") + " "

    # Keys
    keys = item.get("keys", [])

    if isinstance(keys, list):
        searchable_text += " ".join(keys) + " "

    # Job levels
    job_levels = item.get("job_levels", [])

    if isinstance(job_levels, list):
        searchable_text += " ".join(job_levels) + " "

    return searchable_text.lower()

# -----------------------------
# SEARCH FUNCTION
# -----------------------------
def search_assessments(user_query):

    user_query = user_query.lower()

    scored_results = []

    for item in catalog:

        searchable_text = build_search_text(item)

        score = 0

        for word in user_query.split():

            # Strong match in assessment name
            if word in item.get("name", "").lower():
                score += 4

            # Medium match in searchable content
            elif word in searchable_text:
                score += 1

        if score > 0:

            scored_results.append({
                "score": score,
                "name": item.get("name", "Unknown"),
                "url": item.get("link", ""),
                "test_type": item.get("test_type", "Unknown"),
                "description": item.get("description", "")
            })

    # Sort by score
    scored_results.sort(key=lambda x: x["score"], reverse=True)

    # Remove duplicates
    unique_results = []
    seen = set()

    for item in scored_results:

        if item["name"] not in seen:
            unique_results.append(item)
            seen.add(item["name"])

    return unique_results[:10]

# -----------------------------
# CHAT ENDPOINT
# -----------------------------
@app.post("/chat")
def chat(request: ChatRequest):

    # Entire conversation history
    conversation_text = " ".join(
        [msg.content for msg in request.messages]
    ).lower()

    latest_message = request.messages[-1].content.lower()

    # -----------------------------
    # REFUSAL / OUT OF SCOPE
    # -----------------------------
    blocked_topics = [
        "salary",
        "legal",
        "court",
        "religion",
        "politics",
        "hacking",
        "password",
        "crime"
    ]

    for word in blocked_topics:

        if word in conversation_text:
            return {
                "reply": "I can only help with SHL assessment recommendations and comparisons.",
                "recommendations": [],
                "end_of_conversation": False
            }

    # -----------------------------
    # CLARIFICATION
    # -----------------------------
    if len(latest_message.split()) < 4:

        return {
            "reply": "Could you provide more details about the role, seniority level, or required skills?",
            "recommendations": [],
            "end_of_conversation": False
        }

    # -----------------------------
    # COMPARISON FEATURE
    # -----------------------------
    if "compare" in conversation_text or "difference" in conversation_text:

        matched_items = []

        for item in catalog:

            item_name = item.get("name", "").lower()

            if item_name and item_name in conversation_text:
                matched_items.append(item)

        if len(matched_items) >= 2:

            item1 = matched_items[0]
            item2 = matched_items[1]

            comparison_reply = (
                f"{item1['name']} focuses on {item1.get('description', 'general assessment areas')}. "
                f"Whereas {item2['name']} focuses on {item2.get('description', 'general assessment areas')}."
            )

            return {
                "reply": comparison_reply,
                "recommendations": [],
                "end_of_conversation": True
            }

    # -----------------------------
    # RECOMMENDATION SEARCH
    # -----------------------------
    results = search_assessments(conversation_text)

    # No results
    if not results:

        return {
            "reply": "I could not find suitable SHL assessments. Please refine your requirements.",
            "recommendations": [],
            "end_of_conversation": False
        }

    # Format recommendations
    recommendations = []

    for item in results:

        recommendations.append({
            "name": item["name"],
            "url": item["url"],
            "test_type": item["test_type"]
        })

    # -----------------------------
    # FINAL RESPONSE
    # -----------------------------
    return {
        "reply": f"Based on your requirements, I found {len(recommendations)} suitable SHL assessments.",
        "recommendations": recommendations,
        "end_of_conversation": True
    }