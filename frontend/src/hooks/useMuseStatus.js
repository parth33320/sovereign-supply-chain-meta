import { useState, useEffect } from 'react'

export function useMuseStatus() {
  const [status, setStatus] = useState({ state: 'checking', isLive: false, loading: true })

  useEffect(() => {
    let cancelled = false
    async function fetchStatus() {
      try {
        const res = await fetch('/api/vr/muse-status')
        const data = await res.json()
        if (!cancelled) {
          setStatus({
            state: data.state || 'error',
            isLive: data.state === 'live',
            loading: false
          })
        }
      } catch {
        if (!cancelled) {
          setStatus({ state: 'error', isLive: false, loading: false })
        }
      }
    }
    fetchStatus()
    return () => { cancelled = true }
  }, [])

  return status
}

export function museStatusLabel(status) {
  if (status.isLive) return 'Meta Muse-Spark-1.3'
  if (status.state === 'demo') return 'Demo Mode'
  if (status.state === 'no_key') return 'Meta Muse (Demo)'
  if (status.state === 'invalid_key') return 'Meta Muse (Invalid Key)'
  if (status.state === 'unreachable') return 'Meta Muse (Offline)'
  return 'Meta Muse (Demo)'
}