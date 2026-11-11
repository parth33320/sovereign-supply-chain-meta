const BASE = import.meta.env.DEV ? '' : ''

export async function sendChat(message, threadId, tenantId = 'Tenant_A') {
  const r = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      thread_id: threadId,
      tenant_id: tenantId
    })
  })
  if (!r.ok) {
    const err = new Error(`Chat failed: ${r.status}`)
    err.status = r.status
    throw err
  }
  return r.json()
}

export async function getInventory(tenantId = 'Tenant_A') {
  const r = await fetch(`${BASE}/api/inventory?tenant_id=${encodeURIComponent(tenantId)}`)
  if (!r.ok) throw new Error(`Inventory fetch failed: ${r.status}`)
  return r.json()
}

export async function getHealth() {
  const r = await fetch(`${BASE}/health`)
  if (!r.ok) throw new Error(`Health check failed: ${r.status}`)
  return r.json()
}

export async function getManagerPending() {
  const r = await fetch(`${BASE}/api/manager/pending`)
  if (!r.ok) throw new Error(`Failed to fetch pending requests: ${r.status}`)
  return r.json()
}

export async function approveManagerRequest(requestId) {
  const r = await fetch(`${BASE}/api/manager/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_id: requestId })
  })
  if (!r.ok) throw new Error(`Approve failed: ${r.status}`)
  return r.json()
}

export async function rejectManagerRequest(requestId) {
  const r = await fetch(`${BASE}/api/manager/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_id: requestId })
  })
  if (!r.ok) throw new Error(`Reject failed: ${r.status}`)
  return r.json()
}

export async function uploadFile(file) {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch(`${BASE}/api/upload`, {
    method: 'POST', body: fd
  })
  if (!r.ok) throw new Error(`Upload failed: ${r.status}`)
  return r.json()
}

export async function sendVoice(blob) {
  const fd = new FormData()
  fd.append('file', blob, 'recording.wav')
  const r = await fetch(`${BASE}/api/voice`, {
    method: 'POST', body: fd
  })
  if (!r.ok) throw new Error(`Voice failed: ${r.status}`)
  return r.json()
}

export async function approveHITL(threadId, tenantId = 'Tenant_A') {
  const r = await fetch(`${BASE}/api/hitl/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId,
                           tenant_id: tenantId })
  })
  return r.json()
}

export async function rejectHITL(threadId, tenantId = 'Tenant_A') {
  const r = await fetch(`${BASE}/api/hitl/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId,
                           tenant_id: tenantId })
  })
  return r.json()
}

export function createActivityStream(threadId, onEvent) {
  const url = `${BASE}/api/activity/stream?thread_id=${threadId}`
  const es = new EventSource(url)
  es.onmessage = e => {
    try { onEvent(JSON.parse(e.data)) }
    catch {}
  }
  es.onerror = () => {
    es.close()
    setTimeout(() => createActivityStream(threadId, onEvent), 2000)
  }
  return es
}

export function friendlyError(err) {
  if (!err) return "Something went wrong. Please try again."
  if (err.blocked) {
    return "⚠️ That input was blocked. Try a supply chain command."
  }
  const msg = (err.message || "").toLowerCase()
  if (msg.includes("failed to fetch") || msg.includes("networkerror") || msg.includes("network error")) {
    return "Could not reach AI services. Check your connection."
  }
  if (msg.includes("timeout") || msg.includes("aborted") || msg.includes("took too long")) {
    return "The AI took too long. Try a simpler request."
  }
  return "Something went wrong. Please try again."
}
