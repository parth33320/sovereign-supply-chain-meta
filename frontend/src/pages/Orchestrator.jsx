import { useState, useEffect, useCallback, useRef } from 'react'
import ChatWindow from '../components/ChatWindow'
import InputBar from '../components/InputBar'
import HITLCard from '../components/HITLCard'
import ActivityLog from '../components/ActivityLog'
import InventoryGrid from '../components/InventoryGrid'
import AgentProgress from '../components/AgentProgress'
import { sendChatStream, cancelChat, uploadFile, sendVoice,
         getVoiceHistory, approveHITL, rejectHITL,
         createActivityStream, friendlyError } from '../api/client'
import { v4 as uuidv4 } from 'uuid'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function Orchestrator() {
  const [messages, setMessages] = useState([])
  const [chatHidden, setChatHidden] = useState(false)
  const [logHidden, setLogHidden] = useState(false)
  const [logEntries, setLogEntries] = useState([])
  const [agentRunning, setAgentRunning] = useState(false)
  const [currentNode, setCurrentNode] = useState(null)
  const [currentLabel, setCurrentLabel] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [pendingPO, setPendingPO] = useState(null)
  const [threadId] = useState(() => uuidv4())
  const [tenantId] = useState('Tenant_A')
  const [disruptionAlert, setDisruptionAlert] = useState(null)
  const [lastUserMessage, setLastUserMessage] = useState(null)
  const [hasError, setHasError] = useState(false)
  const [duplicateWarning, setDuplicateWarning] = useState(null)
  const [voiceWarning, setVoiceWarning] = useState(null)
  const [prefilledInput, setPrefilledInput] = useState(null)
  const esRef = useRef(null)

  const loadVoiceHistory = useCallback(async () => {
    try {
      const history = await getVoiceHistory()
      if (Array.isArray(history) && history.length > 0) {
        const formatted = history.map(h => ({
          ts: (h.timestamp || '').split('T')[1]?.slice(0, 8) || (h.timestamp || '').slice(-8) || 'voice',
          icon: '🎙️',
          source: 'voice',
          msg: `"${h.transcript}"`
        }))
        setLogEntries(prev => {
          const nonVoice = prev.filter(e => e.source !== 'voice')
          return [...nonVoice, ...formatted].slice(-99)
        })
      }
    } catch (e) {
      console.error('Failed to load voice history', e)
    }
  }, [])

  useEffect(() => {
    loadVoiceHistory()
  }, [loadVoiceHistory])

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

  const handleCancel = useCallback(async () => {
    try {
      await cancelChat(threadId)
    } catch (err) {
      console.error('Cancel request failed:', err)
    }
    setAgentRunning(false)
    setCurrentNode(null)
    setCurrentLabel(null)
    addMsg('assistant', 'Request cancelled.')
  }, [threadId])

  const handleSubmit = useCallback(async (text) => {
    if (agentRunning) return
    setLastUserMessage(text)
    setHasError(false)
    addMsg('user', text)
    setAgentRunning(true)
    setCurrentNode('global_oracle')
    setCurrentLabel('Scanning disruptions...')
    try {
      const res = await sendChatStream(text, threadId, tenantId, (progress) => {
        if (progress.node === 'cancelled') {
          setCurrentNode(null)
          setCurrentLabel(null)
        } else {
          setCurrentNode(progress.node)
          setCurrentLabel(progress.label)
        }
      })
      if (res.cancelled) {
        addMsg('assistant', res.response || 'Request cancelled.')
      } else if (res.blocked) {
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
      setCurrentNode(null)
      setCurrentLabel(null)
    }
  }, [agentRunning, threadId, tenantId])

  const handleFile = useCallback(async (file) => {
    setUploading(true)
    setHasError(false)
    setDuplicateWarning(null)
    addMsg('user', `📎 ${file.name}`)

    const fname = (file.name || '').toLowerCase()
    const isShelf = fname.includes('shelf')
    const isInvoice = fname.includes('invoice') || file.type === 'application/pdf'
    const spinnerText = isShelf
      ? 'Analyzing with Meta SAM 3.1...'
      : isInvoice
      ? 'Extracting with muse-image-1.0...'
      : 'Processing file...'

    // Show temporary spinner message in chat
    const tempId = `temp-upload-${Date.now()}`
    setMessages(prev => [...prev, { id: tempId, role: 'assistant', content: `⏳ ${spinnerText}`, isPending: true }])

    try {
      const res = await uploadFile(file)
      // Remove temporary pending message
      setMessages(prev => prev.filter(m => m.id !== tempId))

      if (res.duplicate) {
        // Show as warning toast, not an error
        setDuplicateWarning(`Duplicate invoice detected (first seen: ${res.first_seen || 'earlier'}). Processing skipped.`)
        return
      }
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
        // Find low/empty items and trigger restock negotiation
        const lowItems = segs
          .filter(s => (s.status || '').toUpperCase() === 'LOW' || (s.status || '').toUpperCase() === 'EMPTY')
          .map(s => s.label || s.sku)
          .filter(Boolean)
        const restockCmd = lowItems.length > 0
          ? `Emergency restock needed for ${lowItems.join(', ')} — stockout detected`
          : `Check stock levels and initiate reorder for low inventory items`
        await handleSubmit(restockCmd)
      } else if (res.type === 'invoice') {
        const e = res.extraction || {}
        const items = Array.isArray(e.items)
          ? e.items.map(it => `  • ${it.name || it.item}: ${it.qty || it.quantity || '?'} @ ${it.price || it.unit_price || '?'}`).join('\n')
          : null
        const lines = [
          e.supplier ? `Supplier: ${e.supplier}` : null,
          e.date ? `Date: ${e.date}` : null,
          e.total ? `Total: ${e.total}` : null,
          items ? `Line Items:\n${items}` : null
        ].filter(Boolean).join('\n')
        addMsg('assistant',
          `📄 Document Extraction (Meta Muse Image 1.0):\n` +
          (lines || JSON.stringify(e, null, 2)))
        // Trigger PO approval workflow from invoice
        const supplier = e.supplier || 'supplier'
        const total = e.total || 'quoted amount'
        await handleSubmit(`Process purchase order from ${supplier} for ${total} — awaiting approval`)
      }
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== tempId))
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
    setVoiceWarning(null)
    try {
      const res = await sendVoice(blob, threadId)
      await loadVoiceHistory()

      // Gating check for low confidence
      if (res.status === 'low_confidence') {
        setVoiceWarning({
          transcription: res.transcript,
          confidence: res.confidence,
          intent: res.intent,
          suggestion: res.suggestion
        })
        return
      }

      addMsg('user', `🎙️ "${res.transcript}"`)
      await handleSubmit(res.transcript)
    } catch {
      setHasError(true)
      addMsg('assistant',
        '⚠️ Voice transcription failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }, [handleSubmit, threadId, loadVoiceHistory])

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

      {/* Duplicate Invoice Warning Toast */}
      {duplicateWarning && (
        <div className="mb-3 px-3 py-2 bg-[#d29922]/20 border border-[#d29922] rounded-lg text-xs text-[#f0883e] flex items-center justify-between gap-2 shadow">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>{duplicateWarning}</span>
          </div>
          <button
            onClick={() => setDuplicateWarning(null)}
            className="text-[#8b949e] hover:text-[#e6edf3] font-bold text-xs px-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Voice Confidence Gating Yellow Banner */}
      {voiceWarning && (
        <div className="mb-3 px-3 py-2.5 bg-[#d29922]/20 border border-[#d29922] rounded-lg text-xs text-[#f0883e] space-y-2 shadow">
          <div className="flex items-start justify-between gap-2">
            <div className="space-y-1">
              <p className="font-semibold text-[#e6edf3]">
                🟡 Low confidence transcription ({Math.round((voiceWarning.confidence || 0) * 100)}%): "{voiceWarning.transcription}"
              </p>
              {voiceWarning.suggestion && (
                <p className="text-[#8b949e]">
                  Did you mean: <strong className="text-[#58a6ff]">"{voiceWarning.suggestion}"</strong>?
                </p>
              )}
            </div>
            <button
              onClick={() => setVoiceWarning(null)}
              className="text-[#8b949e] hover:text-[#e6edf3] font-bold text-xs px-1"
            >
              ✕
            </button>
          </div>
          <div className="flex items-center gap-2 pt-1">
            {voiceWarning.suggestion && (
              <button
                onClick={() => {
                  setPrefilledInput(voiceWarning.suggestion)
                  setVoiceWarning(null)
                }}
                className="px-2.5 py-1 bg-[#21262d] hover:bg-[#30363d] text-[#58a6ff] border border-[#30363d] rounded text-[11px] font-semibold transition-colors flex items-center gap-1"
              >
                <span>💡</span> Use suggestion
              </button>
            )}
            <button
              onClick={() => {
                const text = voiceWarning.transcription
                setVoiceWarning(null)
                addMsg('user', `🎙️ "${text}"`)
                handleSubmit(text)
              }}
              className="px-2.5 py-1 bg-[#238636] hover:bg-[#2ea043] text-white rounded text-[11px] font-semibold transition-colors flex items-center gap-1 shadow"
            >
              <span>🎙️</span> Use anyway
            </button>
          </div>
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
        <AgentProgress
          currentNode={currentNode}
          currentLabel={currentLabel}
          itemCount={20}
          stockoutCount={2}
        />
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
        disabled={hitlPending}
        isLoading={agentRunning}
        onCancel={handleCancel}
        prefill={prefilledInput}
        onClearPrefill={() => setPrefilledInput(null)}
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
