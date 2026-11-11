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
  const [loading, setLoading] = useState(false)
  const [pendingPO, setPendingPO] = useState(null)
  const [threadId] = useState(() => uuidv4())
  const [helpShown, setHelpShown] = useState(false)
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
    if (loading) return
    setLastUserMessage(text)
    setHasError(false)
    addMsg('user', text)
    setLoading(true)
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
      setLoading(false)
    }
  }, [loading, threadId, tenantId])

  const handleFile = useCallback(async (file) => {
    setLoading(true)
    setHasError(false)
    addMsg('user', `📎 ${file.name}`)
    try {
      const res = await uploadFile(file)
      if (res.type === 'audio') {
        addMsg('assistant',
          `🎙️ Transcribed: "${res.transcript}"`)
        await handleSubmit(res.transcript)
        return
      }
      if (res.type === 'shelf') {
        const a = res.analysis
        addMsg('assistant',
          `📦 Warehouse Shelf Analysis (Meta SAM 3.1):\n` +
          `${JSON.stringify(a?.summary || a, null, 2)}`)
      } else if (res.type === 'invoice') {
        const e = res.extraction
        addMsg('assistant',
          `📄 Document Extraction (Meta Muse Image 1.0):\n` +
          `${JSON.stringify(e, null, 2)}`)
      }
    } catch (err) {
      setHasError(true)
      addMsg('assistant', friendlyError(err))
    } finally {
      setLoading(false)
    }
  }, [handleSubmit])

  const handleVoice = useCallback(async (blob) => {
    setLoading(true)
    setHasError(false)
    try {
      const res = await sendVoice(blob)
      addMsg('user', `🎙️ "${res.transcript}"`)
      await handleSubmit(res.transcript)
    } catch (err) {
      setHasError(true)
      addMsg('assistant', friendlyError(err))
    } finally {
      setLoading(false)
    }
  }, [handleSubmit])

  const handleApprove = async () => {
    setLoading(true)
    try {
      const res = await approveHITL(threadId, tenantId)
      addMsg('assistant',
        `✅ PO approved and dispatched. ETA ${
          pendingPO?.lead_time || '?'} days.`)
      setPendingPO(null)
    } catch (err) {
      addMsg('assistant', friendlyError(err))
    } finally {
      setLoading(false)
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

  const handleHelp = () => {
    if (helpShown) return
    setHelpShown(true)
    addMsg('assistant',
      `Autonomous supply chain orchestration powered by Meta AI.\n\n` +
      `Try these commands:\n` +
      `• Check stock levels for Widget-A\n` +
      `• Reorder 500 Microcontrollers\n` +
      `• Emergency restock Semiconductors\n\n` +
      `Upload files via 📎: shelf images, invoices, or voice commands.`)
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

        <div className="flex items-center gap-2 text-xs">
          {disruptionAlert ? (
            <span className="bg-[#b62324]/20 text-[#ff7b72] border border-[#b62324]/40 font-semibold px-2 py-0.5 rounded-full flex items-center gap-1">
              🔔 1 ALERT
            </span>
          ) : (
            <span className="bg-[#238636]/20 text-[#3fb950] border border-[#238636]/40 font-medium px-2 py-0.5 rounded-full flex items-center gap-1">
              🟢 Operational
            </span>
          )}
        </div>
      </div>

      {/* Live Inventory Grid above ChatWindow */}
      <InventoryGrid
        tenantId={tenantId}
        onSelectStockout={(itemName) => {
          handleSubmit(`Emergency restock needed for ${itemName}`)
        }}
      />

      {/* Agent multi-step progress indicator when loading */}
      {loading && (
        <AgentProgress itemCount={20} stockoutCount={2} />
      )}

      {/* Empty State Onboarding Card (shown when messages.length === 0 and !loading) */}
      {messages.length === 0 && !loading && (
        <div className="mb-4 bg-[#161b22] border border-[#30363d] rounded-lg p-5 text-center">
          <h2 className="text-sm font-semibold text-[#e6edf3] mb-1">
            👋 Welcome to Sovereign Supply Chain
          </h2>
          <p className="text-xs text-[#8b949e] mb-4">
            Autonomous multi-agent logistics control tower
          </p>
          <div className="flex flex-col sm:flex-row gap-2 justify-center">
            <button
              onClick={() => handleSubmit("Microcontrollers are out of stock — negotiate now")}
              className="text-xs bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] border border-[#30363d] py-1.5 px-3 rounded text-left transition-colors"
            >
              🔴 Microcontrollers are out of stock — negotiate now
            </button>
            <button
              onClick={() => handleSubmit("Check semiconductor levels across all hubs")}
              className="text-xs bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] border border-[#30363d] py-1.5 px-3 rounded text-left transition-colors"
            >
              📦 Check semiconductor levels across all hubs
            </button>
            <button
              onClick={() => handleSubmit("Negotiate restock with Supplier B")}
              className="text-xs bg-[#21262d] hover:bg-[#30363d] text-[#e6edf3] border border-[#30363d] py-1.5 px-3 rounded text-left transition-colors"
            >
              🤝 Negotiate restock with Supplier B
            </button>
          </div>
        </div>
      )}

      <ChatWindow
        messages={messages}
        hidden={chatHidden}
        onToggle={() => setChatHidden(p => !p)}
        onClear={() => !hitlPending && setMessages([])}
        disabled={hitlPending}
      />

      {/* Friendly Try Again button if error occurred */}
      {hasError && lastUserMessage && !loading && (
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

      <InputBar
        onSubmit={handleSubmit}
        onFileUpload={handleFile}
        onVoice={handleVoice}
        onHelpClick={handleHelp}
        disabled={hitlPending || loading}
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
