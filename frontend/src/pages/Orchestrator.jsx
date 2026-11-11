import { useState, useEffect, useCallback, useRef } from 'react'
import ChatWindow from '../components/ChatWindow'
import InputBar from '../components/InputBar'
import HITLCard from '../components/HITLCard'
import ActivityLog from '../components/ActivityLog'
import InventoryGrid from '../components/InventoryGrid'
import AgentProgress from '../components/AgentProgress'
import { sendChat, uploadFile, sendVoice,
         approveHITL, rejectHITL,
         createActivityStream, friendlyError } from '../api/client'
import { v4 as uuidv4 } from 'uuid'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function Orchestrator() {
  const [messages, setMessages] = useState([])
  const [chatHidden, setChatHidden] = useState(false)
  const [logHidden, setLogHidden] = useState(false)
  const [logEntries, setLogEntries] = useState([])
  const [agentRunning, setAgentRunning] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [pendingPO, setPendingPO] = useState(null)
  const [threadId] = useState(() => uuidv4())
  const [tenantId] = useState('Tenant_A')
  const [disruptionAlert, setDisruptionAlert] = useState(null)
  const [lastUserMessage, setLastUserMessage] = useState(null)
  const [hasError, setHasError] = useState(false)
  const esRef = useRef(null)

  useEffect(() => {
    esRef.current = createActivityStream(threadId, (entry) => {
      setLogEntries(prev => [...prev.slice(-99), entry])
    })
    return () => esRef.current?.close()
  }, [threadId])

  const addMsg = (role, content) =>
    setMessages(prev => [...prev, { role, content }])

  const checkForDisruption = (text) => {
    if (!text || typeof text !== 'string') return
    // Check if response contains [GLOBAL ORACLE ALERT] with HIGH or MEDIUM
    if (text.includes('[GLOBAL ORACLE ALERT]')) {
      const isHigh = text.includes('HIGH')
      const isMedium = text.includes('MEDIUM')
      if (isHigh || isMedium) {
        // Extract summary if present
        const parts = text.split('[GLOBAL ORACLE ALERT]')
        const alertPart = parts[1] || ''
        const summary = alertPart.split('\n')[0].replace(/^\s*\((HIGH|MEDIUM)\):\s*/i, '').trim() ||
                        'Severe disruption reported in critical transit lanes.'
        setDisruptionAlert({
          severity: isHigh ? 'HIGH' : 'MEDIUM',
          summary: summary
        })
      }
    }
  }

  const handleSubmit = useCallback(async (text) => {
    if (agentRunning) return
    setLastUserMessage(text)
    setHasError(false)
    addMsg('user', text)
    setAgentRunning(true)
    try {
      const res = await sendChat(text, threadId, tenantId)
      if (res.blocked) {
        addMsg('assistant', friendlyError({ blocked: true }))
      } else {
        addMsg('assistant', res.response)
        checkForDisruption(res.response)
        if (res.hitl_required && res.pending_po) {
          setPendingPO(res.pending_po)
        }
      }
    } catch (e) {
      setHasError(true)
      addMsg('assistant', friendlyError(e))
    } finally {
      setAgentRunning(false)
    }
  }, [agentRunning, threadId, tenantId])

  const handleFile = useCallback(async (file) => {
    setUploading(true)
    setHasError(false)
    addMsg('user', `📎 ${file.name}`)

    const fname = (file.name || '').toLowerCase()
    let spinnerText = 'Processing file...'
    if (fname.includes('shelf')) {
      spinnerText = 'Analyzing with Meta SAM 3.1...'
    } else if (fname.includes('invoice') || fname.endsWith('.pdf')) {
      spinnerText = 'Extracting with muse-image-1.0...'
    } else if (file.type?.startsWith('audio/') || fname.endsWith('.wav') || fname.endsWith('.mp3')) {
      spinnerText = 'Transcribing voice with muse-voice-transcribe-1.0...'
    }

    const spinnerMsgId = Date.now()
    setMessages(prev => [...prev, { id: spinnerMsgId, role: 'assistant', content: spinnerText, loading: true }])

    try {
      const res = await uploadFile(file)
      setMessages(prev => prev.filter(m => m.id !== spinnerMsgId))

      if (res.error) {
        addMsg('assistant', `⚠️ ${res.error}`)
        return
      }
      if (res.type === 'audio') {
        addMsg('assistant',
          `🎙️ Transcribed: "${res.transcript}"`)
        await handleSubmit(res.transcript)
        return
      }
      if (res.type === 'shelf') {
        const segs = res.analysis?.segments || []
        const lines = segs.map(s =>
          `${s.label || s.sku || 'Item'}: ` +
          `${s.fill_pct ?? s.fill_level ?? '?'}% — ` +
          `${s.status || 'unknown'}`
        ).join('\n')
        addMsg('assistant',
          `📦 Warehouse Shelf Analysis (Meta SAM 3.1):\n` +
          (lines || res.analysis?.summary || JSON.stringify(res.analysis, null, 2)))
      } else if (res.type === 'invoice') {
        const e = res.extraction || {}
        const items = (e.items || []).map(item => `  • ${item.name || item.sku || 'Item'}: ${item.qty || '?'} @ ${item.price || '?'}`).join('\n')
        const lines = [
          e.supplier ? `Supplier: ${e.supplier}` : null,
          e.total ? `Total: ${e.total}` : null,
          e.date ? `Date: ${e.date}` : null,
          items ? `Items:\n${items}` : null
        ].filter(Boolean).join('\n')
        addMsg('assistant',
          `📄 Document Extraction (Meta Muse Image 1.0):\n` +
          (lines || JSON.stringify(e, null, 2)))
      }
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== spinnerMsgId))
      setHasError(true)
      addMsg('assistant',
        `⚠️ Upload failed: ${friendlyError(err)}`)
    } finally {
      setUploading(false)
    }
  }, [handleSubmit])

  const handleVoice = useCallback(async (blob) => {
    setUploading(true)
    setHasError(false)
    try {
      const res = await sendVoice(blob)
      addMsg('user', `🎙️ "${res.transcript}"`)
      await handleSubmit(res.transcript)
    } catch {
      setHasError(true)
      addMsg('assistant',
        '⚠️ Voice transcription failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }, [handleSubmit])

  const handleApprove = async () => {
    setAgentRunning(true)
    try {
      await approveHITL(threadId, tenantId)
      addMsg('assistant',
        `✅ PO approved and dispatched. ETA ${
          pendingPO?.lead_time || '?'} days.`)
      setPendingPO(null)
    } catch (err) {
      addMsg('assistant', friendlyError(err))
    } finally {
      setAgentRunning(false)
    }
  }

  const handleReject = async () => {
    addMsg('assistant', '❌ PO rejected. No order placed.')
    try {
      await rejectHITL(threadId, tenantId)
    } catch (err) {
      console.error(err)
    }
    setPendingPO(null)
  }

  const hitlPending = !!pendingPO

  return (
    <div className="flex-1 flex flex-col p-4 overflow-hidden max-w-4xl mx-auto w-full">
      {/* Disruption Alert Top Banner */}
      {disruptionAlert && (
        <div className="mb-3 px-3 py-2 bg-[#b62324]/20 border border-[#b62324] rounded-lg text-xs text-[#ff7b72] flex items-center gap-2">
          <AlertTriangle size={15} className="shrink-0" />
          <span>
            <strong>⚠️ {disruptionAlert.severity} DISRUPTION ALERT</strong> — {disruptionAlert.summary}
          </span>
        </div>
      )}

      {/* Header bar */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-base font-semibold text-[#e6edf3]">
          Orchestrator
        </h1>

        {disruptionAlert && (
          <div className="flex items-center gap-2 text-xs">
            <span className="bg-[#b62324]/20 text-[#ff7b72] border border-[#b62324]/40 font-semibold px-2 py-0.5 rounded-full flex items-center gap-1">
              🔔 1 ALERT
            </span>
          </div>
        )}
      </div>

      {/* Live Inventory Grid above ChatWindow */}
      <InventoryGrid
        tenantId={tenantId}
        onSelectStockout={(itemName) => {
          handleSubmit(`Emergency restock needed for ${itemName}`)
        }}
      />

      {/* Agent multi-step progress indicator when agentRunning */}
      {agentRunning && (
        <AgentProgress itemCount={20} stockoutCount={2} />
      )}

      <ChatWindow
        messages={messages}
        hidden={chatHidden}
        onToggle={() => setChatHidden(p => !p)}
        onClear={() => !hitlPending && setMessages([])}
        disabled={hitlPending}
      />

      {/* Friendly Try Again button if error occurred */}
      {hasError && lastUserMessage && !agentRunning && (
        <div className="my-2 flex justify-start">
          <button
            onClick={() => handleSubmit(lastUserMessage)}
            className="flex items-center gap-1.5 text-xs bg-[#21262d] hover:bg-[#30363d] text-[#58a6ff] border border-[#30363d] px-3 py-1.5 rounded transition-colors"
          >
            <RefreshCw size={13} />
            <span>🔄 Try again</span>
          </button>
        </div>
      )}

      {hitlPending && (
        <HITLCard
          po={pendingPO}
          threadId={threadId}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}

      {uploading && (
        <div className="flex items-center gap-2 text-xs text-[#8b949e] mb-2 px-1">
          <div className="w-3 h-3 border border-[#58a6ff] border-t-transparent rounded-full animate-spin" />
          <span>Processing file...</span>
        </div>
      )}

      <InputBar
        onSubmit={handleSubmit}
        onFileUpload={handleFile}
        onVoice={handleVoice}
        disabled={hitlPending || agentRunning}
      />

      <ActivityLog
        entries={logEntries}
        hidden={logHidden}
        onToggle={() => setLogHidden(p => !p)}
        onClear={() => !hitlPending && setLogEntries([])}
        disabled={hitlPending}
      />
    </div>
  )
}
