import { useState, useEffect, useCallback, useRef } from 'react'
import ChatWindow from '../components/ChatWindow'
import InputBar from '../components/InputBar'
import HITLCard from '../components/HITLCard'
import ActivityLog from '../components/ActivityLog'
import { sendChat, uploadFile, sendVoice,
         approveHITL, rejectHITL,
         createActivityStream } from '../api/client'
import { v4 as uuidv4 } from 'uuid'

export default function Orchestrator() {
  const [messages, setMessages] = useState([])
  const [chatHidden, setChatHidden] = useState(false)
  const [logHidden, setLogHidden] = useState(false)
  const [logEntries, setLogEntries] = useState([])
  const [loading, setLoading] = useState(false)
  const [pendingPO, setPendingPO] = useState(null)
  const [threadId] = useState(() => uuidv4())
  const [helpShown, setHelpShown] = useState(false)
  const esRef = useRef(null)

  useEffect(() => {
    esRef.current = createActivityStream(threadId, (entry) => {
      setLogEntries(prev => [...prev.slice(-99), entry])
    })
    return () => esRef.current?.close()
  }, [threadId])

  const addMsg = (role, content) =>
    setMessages(prev => [...prev, { role, content }])

  const handleSubmit = useCallback(async (text) => {
    if (loading) return
    addMsg('user', text)
    setLoading(true)
    try {
      const res = await sendChat(text, threadId)
      addMsg('assistant', res.response)
      if (res.hitl_required && res.pending_po) {
        setPendingPO(res.pending_po)
      }
    } catch (e) {
      addMsg('assistant',
        '⚠️ Unable to complete request. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [loading, threadId])

  const handleFile = useCallback(async (file) => {
    setLoading(true)
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
      addMsg('assistant',
        `⚠️ Upload failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [handleSubmit])

  const handleVoice = useCallback(async (blob) => {
    setLoading(true)
    try {
      const res = await sendVoice(blob)
      addMsg('user', `🎙️ "${res.transcript}"`)
      await handleSubmit(res.transcript)
    } catch {
      addMsg('assistant',
        '⚠️ Voice transcription failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [handleSubmit])

  const handleApprove = async () => {
    setLoading(true)
    const res = await approveHITL(threadId)
    addMsg('assistant',
      `✅ PO approved and dispatched. ETA ${
        pendingPO?.lead_time || '?'} days.`)
    setPendingPO(null)
    setLoading(false)
  }

  const handleReject = async () => {
    addMsg('assistant', '❌ PO rejected. No order placed.')
    await rejectHITL(threadId)
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
    <div className="flex-1 flex flex-col p-4 overflow-hidden
                    max-w-4xl mx-auto w-full">
      <h1 className="text-lg font-semibold text-[#e6edf3] mb-4">
        Orchestrator
      </h1>

      {loading && (
        <div className="flex items-center gap-2 text-sm
                        text-[#8b949e] mb-2">
          <div className="w-4 h-4 border-2 border-[#58a6ff]
                          border-t-transparent rounded-full
                          animate-spin" />
          <span>AI agents working...</span>
        </div>
      )}

      <ChatWindow
        messages={messages}
        hidden={chatHidden}
        onToggle={() => setChatHidden(p => !p)}
        onClear={() => !hitlPending && setMessages([])}
        disabled={hitlPending}
      />

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
