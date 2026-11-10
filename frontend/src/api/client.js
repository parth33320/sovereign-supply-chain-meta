const BASE = import.meta.env.DEV ? '' : ''

export async function sendChat(message, threadId) {
  const r = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      thread_id: threadId,
      tenant_id: 'Tenant_A'
    })
  })
  if (!r.ok) throw new Error(`Chat failed: ${r.status}`)
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

export async function approveHITL(threadId) {
  const r = await fetch(`${BASE}/api/hitl/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId,
                           tenant_id: 'Tenant_A' })
  })
  return r.json()
}

export async function rejectHITL(threadId) {
  const r = await fetch(`${BASE}/api/hitl/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId,
                           tenant_id: 'Tenant_A' })
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
