"""CampusConnect event and registration API."""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from postgrest import APIError
from supabase import Client, create_client

load_dotenv()

app = Flask(__name__)


def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY must be set")
    return create_client(url, key)


supabase = get_supabase()


def api_error(message: str, status: int):
    return jsonify({"error": message}), status


def error_code(error: APIError) -> str | None:
    code = getattr(error, "code", None)
    if code:
        return str(code)
    if isinstance(getattr(error, "json", None), dict):
        value = error.json.get("code")
        return str(value) if value else None
    return None


@app.get("/")
def index():
    return jsonify({"name": "CampusConnect API", "status": "ok", "endpoints": [
        "GET /api/events",
        "GET /api/events/<id>",
        "POST /api/registrations",
        "GET /api/me/registrations?user_id=<uuid>",
        "GET /api/events/<id>/registrations",
    ]})


@app.get("/api/events")
def list_events():
    """Browse events, optionally filtering by status and paging results."""
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return api_error("limit and offset must be integers", 400)

    query = supabase.table("events").select("*")
    status = request.args.get("status")
    if status:
        query = query.eq("status", status)
    try:
        result = query.order("title").range(offset, offset + limit - 1).execute()
        return jsonify({"data": result.data, "limit": limit, "offset": offset})
    except APIError as error:
        app.logger.exception("Could not list events")
        return api_error("Could not load events", 502)


@app.get("/api/events/<event_id>")
def get_event(event_id: str):
    try:
        result = supabase.table("events").select("*").eq("id", event_id).limit(1).execute()
        if not result.data:
            return api_error("Event not found", 404)
        return jsonify({"data": result.data[0]})
    except APIError as error:
        app.logger.exception("Could not load event")
        return api_error("Could not load event", 502)


@app.post("/api/registrations")
def create_registration():
    """Create a registration. Without auth, clients must supply user_id."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error("Request body must be a JSON object", 400)
    user_id = payload.get("user_id")
    event_id = payload.get("event_id")
    if not user_id or not event_id:
        return api_error("user_id and event_id are required", 400)

    try:
        # Check event status/capacity before inserting. PostgreSQL constraints should
        # still enforce uniqueness and referential integrity in the database.
        event_result = supabase.table("events").select("id,capacity,status").eq("id", event_id).limit(1).execute()
        if not event_result.data:
            return api_error("Event not found", 404)
        event = event_result.data[0]
        if str(event.get("status") or "").lower() in ("closed", "cancelled", "canceled", "full", "draft"):
            return api_error("Event is not accepting registrations", 409)

        if event.get("capacity") is not None:
            count_result = supabase.table("registrations").select("id", count="exact").eq("event_id", event_id).execute()
            if (count_result.count or 0) >= event["capacity"]:
                return api_error("Event is at capacity", 409)

        result = supabase.table("registrations").insert({
            "user_id": user_id,
            "event_id": event_id,
        }).execute()
        return jsonify({"data": result.data[0] if result.data else None}), 201
    except APIError as error:
        app.logger.exception("Could not create registration")
        if error_code(error) == "23505":
            return api_error("User is already registered for this event", 409)
        if error_code(error) == "23503":
            return api_error("user_id or event_id does not exist", 400)
        return api_error("Could not create registration", 502)


@app.get("/api/me/registrations")
def list_user_registrations():
    """List registrations for an explicitly supplied user UUID (no login)."""
    user_id = request.args.get("user_id")
    if not user_id:
        return api_error("user_id query parameter is required", 400)
    try:
        result = supabase.table("registrations").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return jsonify({"data": result.data})
    except APIError as error:
        app.logger.exception("Could not load user registrations")
        return api_error("Could not load registrations", 502)


@app.get("/api/events/<event_id>/registrations")
def list_event_registrations(event_id: str):
    """List attendee registrations for an event; this route is public."""
    try:
        event_result = supabase.table("events").select("id").eq("id", event_id).limit(1).execute()
        if not event_result.data:
            return api_error("Event not found", 404)
        result = supabase.table("registrations").select("*").eq("event_id", event_id).order("created_at", desc=True).execute()
        return jsonify({"data": result.data})
    except APIError as error:
        app.logger.exception("Could not load event registrations")
        return api_error("Could not load registrations", 502)


@app.errorhandler(404)
def not_found(_error):
    return api_error("Route not found", 404)


@app.errorhandler(500)
def internal_error(_error):
    return api_error("Internal server error", 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
