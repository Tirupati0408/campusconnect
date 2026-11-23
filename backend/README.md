# CampusConnect backend

Flask JSON API backed by the Supabase tables shown in `database.png`: `events`, `users`, and `registrations`.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` there.
4. Start with `python app.py`. The API listens on port 5000 by default; set `PORT` to change it.

## Deploy to Render

This folder is ready to deploy as the root of its own Git repository. Upload the contents of `backend` (including `render.yaml` and `.python-version`) to GitHub, then in Render choose **New +** → **Blueprint** and connect that repository. Render installs `requirements.txt`, starts `gunicorn app:app`, and checks `/` for health. In the Render service environment, set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` using your Supabase project values. Do not upload `.env`; `.gitignore` excludes it. `.env.example` is a safe template for local setup.

If you keep this folder inside a larger repository, configure Render's service `rootDir` as `backend` and point Render to `backend/render.yaml` as the Blueprint file.

The Render service needs anonymous Supabase grants and RLS policies that allow the routes it uses. A successful Render deploy alone does not confirm database access.

## Endpoints

All responses use JSON. Errors have the form `{"error":"..."}`. Lists return `{"data":[...]}`.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/` | API status and endpoint list |
| GET | `/api/events?status=open&limit=50&offset=0` | Browse events, optionally filter by status and paginate |
| GET | `/api/events/<id>` | Event details; 404 if missing |
| POST | `/api/registrations` | Create a registration; returns 201, or 409 for duplicate/full/closed event |
| GET | `/api/me/registrations?user_id=<uuid>` | List registrations for the supplied user |
| GET | `/api/events/<id>/registrations` | List attendees for an event |

Registration request body:

```json
{
  "user_id": "<existing users.id UUID>",
  "event_id": "<existing events.id UUID>"
}
```

## Access model

This backend intentionally has no authentication or authorization. `user_id` is supplied by the caller, and the personal-registration and attendee-list routes are public. Consequently, callers can request another user's registrations and read attendee lists. The original endpoint sketch marked these routes private; this implementation follows the request to omit access controls.

The supplied `.env` uses a Supabase publishable key, which is evaluated as the `anon` database role when no user session is present. Supabase table grants and RLS policies still apply, so the Supabase project must permit the intended anonymous reads and inserts for these routes to work. This code does not change database grants or RLS policies.

The event capacity check is performed before insert. For concurrent registrations, add a database-side atomic capacity constraint/function if strict capacity enforcement is required. A unique constraint on `(user_id, event_id)` is also needed for reliable duplicate prevention.
