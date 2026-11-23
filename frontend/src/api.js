const configuredApiBase = (import.meta.env.VITE_API_BASE_URL || '').trim()
const API_BASE = (configuredApiBase || 'https://campusconnect-1-lq2y.onrender.com')
  .replace(/\.onrender\.comy(?=\/|$)/i, '.onrender.com')
  .replace(/\/$/, '')

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
    })
  } catch {
    throw new Error(`Could not reach the API at ${API_BASE}. Check that the backend is awake and allows browser requests.`)
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error || `The request failed (${response.status}).`)
  return data
}

async function requestList(path, options) {
  const payload = await request(path, options)
  if (Array.isArray(payload)) return payload
  return Array.isArray(payload?.data) ? payload.data : []
}

export const apiBase = API_BASE
export const getEvents = () => requestList('/api/events')
export const getEvent = (id) => request(`/api/events/${encodeURIComponent(id)}`)
export const getMyRegistrations = (userId) => requestList(`/api/me/registrations?user_id=${encodeURIComponent(userId)}`)
export const registerForEvent = (userId, eventId) => request('/api/registrations', {
  method: 'POST', body: JSON.stringify({ user_id: userId, event_id: eventId }),
})
export const getEventRegistrations = (eventId, organizerId) => requestList(
  `/api/events/${encodeURIComponent(eventId)}/registrations?organizer_id=${encodeURIComponent(organizerId)}`,
)
