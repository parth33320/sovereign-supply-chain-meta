const BASE = import.meta.env.DEV ? '' : ''

export async function sendChatStream(message, threadId, tenantId = 'Tenant_A', onProgress) {
  const response = await fetch(`${BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      thread_id: threadId,
      tenant_id: tenantId
    })
  })
  if (!response.ok) {
    const err = new Error(`Chat stream failed: ${response.status}`)
    err.status = response.status
    throw err
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let finalResult = null
  let buffer = ''

  const processChunk = (chunk) => {
    buffer += chunk
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data:')) continue
      try {
        const data = JSON.parse(line.replace(/^data:\s*/, ''))
        if (data.node === 'cancelled') {
          if (onProgress) onProgress(data)
          return { cancelled: true, response: data.label || 'Request cancelled.' }
        }
        if (data.blocked || data.node === 'complete' || data.response !== undefined) {
          finalResult = data
        } else if (onProgress) {
          onProgress(data)
        }
      } catch {}
    }
    return null
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      // Flush remaining buffer — append sentinel so the split captures the last event
      if (buffer.trim()) {
        processChunk('\n\n')
      }
      break
    }
    const earlyReturn = processChunk(decoder.decode(value, { stream: true }))
    if (earlyReturn) return earlyReturn
  }

  return finalResult || { response: 'Completed.' }
}

export async function cancelChat(threadId) {
  const r = await fetch(`${BASE}/api/chat/${encodeURIComponent(threadId)}`, {
    method: 'DELETE'
  })
  return r.json()
}

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

export async function getKPIs(tenantId = 'Tenant_A') {
  const r = await fetch(`${BASE}/api/kpi?tenant_id=${encodeURIComponent(tenantId)}`)
  if (!r.ok) throw new Error(`KPI fetch failed: ${r.status}`)
  return r.json()
}

export async function getHealth() {
  const r = await fetch(`${BASE}/health`)
  if (!r.ok) throw new Error(`Health check failed: ${r.status}`)
  return r.json()
}

export async function loginManager() {
  const r = await fetch(`${BASE}/api/manager/login`)
  if (!r.ok) throw new Error(`Manager login failed: ${r.status}`)
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

export async function sendVoice(blob, threadId) {
  const fd = new FormData()
  fd.append('file', blob, 'recording.wav')
  if (threadId) {
    fd.append('thread_id', threadId)
  }
  const r = await fetch(`${BASE}/api/voice`, {
    method: 'POST', body: fd
  })
  if (!r.ok) throw new Error(`Voice failed: ${r.status}`)
  return r.json()
}

export async function getVoiceHistory() {
  const r = await fetch(`${BASE}/api/voice/history`)
  if (!r.ok) throw new Error(`Voice history failed: ${r.status}`)
  return r.json()
}

export async function runWhatIf(scenario, threadId, tenantId = 'Tenant_A') {
  const r = await fetch(`${BASE}/api/whatif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenario,
      thread_id: threadId,
      tenant_id: tenantId
    })
  })
  if (!r.ok) throw new Error(`What-if simulation failed: ${r.status}`)
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
