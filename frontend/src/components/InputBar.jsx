import { useState, useRef, useEffect } from 'react'
import { Paperclip, Mic, Send, HelpCircle, X } from 'lucide-react'
import Tooltip from './Tooltip'

export default function InputBar({ onSubmit, onFileUpload, onVoice, disabled, isLoading, onCancel, prefill, onClearPrefill }) {
  const [text, setText] = useState('')

  useEffect(() => {
    if (prefill) {
      setText(prefill)
      if (onClearPrefill) onClearPrefill()
    }
  }, [prefill, onClearPrefill])
  const [mode, setMode] = useState(null)
  const [recording, setRecording] = useState(false)
  const fileRef = useRef(null)
  const mediaRef = useRef(null)
  const chunksRef = useRef([])

  const toggleMode = (m) => setMode(prev => prev === m ? null : m)

  const handleSend = () => {
    if (!text.trim() || disabled) return
    onSubmit(text.trim())
    setText('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setMode(null)
    await onFileUpload(file)
    e.target.value = ''
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      chunksRef.current = []
      mr.ondataavailable = e => chunksRef.current.push(e.data)
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })
        stream.getTracks().forEach(t => t.stop())
        setRecording(false)
        setMode(null)
        await onVoice(blob)
      }
      mr.start()
      mediaRef.current = mr
      setRecording(true)
    } catch {
      alert('Microphone access denied')
    }
  }

  const stopRecording = () => mediaRef.current?.stop()

  return (
    <div className="mt-2">
      {mode === 'file' && (
        <div className="mb-2 border border-[#30363d] rounded-lg
                        p-3 bg-[#161b22] flex items-center
                        justify-between">
          <label className="cursor-pointer text-sm
                            text-[#58a6ff] hover:underline">
            📎 Choose file (WAV, PNG, JPG, PDF — max 10MB)
            <input ref={fileRef} type="file" className="hidden"
                   accept=".wav,.mp3,.ogg,.png,.jpg,.jpeg,
                           .webp,.pdf"
                   onChange={handleFile} />
          </label>
          <button onClick={() => setMode(null)}>
            <X size={14} className="text-[#8b949e]
                                    hover:text-[#e6edf3]" />
          </button>
        </div>
      )}

      {mode === 'voice' && (
        <div className="mb-2 border border-[#30363d] rounded-lg
                        p-3 bg-[#161b22] flex items-center
                        justify-between">
          {recording ? (
            <button onClick={stopRecording}
                    className="text-sm text-[#f85149]
                               hover:text-red-400 font-medium">
              ⏹ Stop & Send Recording
            </button>
          ) : (
            <button onClick={startRecording}
                    className="text-sm text-[#58a6ff]
                               hover:text-blue-400">
              🎙️ Click to start recording
            </button>
          )}
          <button onClick={() => setMode(null)}>
            <X size={14} className="text-[#8b949e]
                                    hover:text-[#e6edf3]" />
          </button>
        </div>
      )}

      <div className="flex items-center gap-1 border
                      border-[#30363d] rounded-lg bg-[#161b22]
                      px-2 py-1">
        <Tooltip
          position="top"
          content={
            <div className="space-y-3">
              <p className="font-semibold text-[#e6edf3] text-xs">
                How to use this interface
              </p>
              <div className="space-y-2 text-[#8b949e]">
                <div>
                  <span className="text-[#e6edf3] font-medium">
                    📎 Attach file
                  </span>
                  <p className="mt-0.5">
                    Shelf image → AI scans stock levels<br/>
                    Invoice/BOL → AI extracts supplier & line items<br/>
                    Audio file → AI transcribes your voice command
                  </p>
                </div>
                <div>
                  <span className="text-[#e6edf3] font-medium">
                    🎙️ Record voice
                  </span>
                  <p className="mt-0.5">
                    Click mic, speak your command, click stop.
                    Audio is transcribed and processed automatically.
                  </p>
                </div>
                <div>
                  <span className="text-[#e6edf3] font-medium">
                    ✍️ Type a command
                  </span>
                  <p className="mt-0.5">
                    "Check stock levels for Widget-A"<br/>
                    "Emergency restock Semiconductors"<br/>
                    "Reorder 500 Microcontrollers"
                  </p>
                </div>
              </div>
            </div>
          }
        >
          <button
            disabled={disabled}
            className="p-1.5 rounded text-[#8b949e]
                       hover:text-[#e6edf3] hover:bg-[#21262d]
                       transition-colors disabled:opacity-30 shrink-0">
            <HelpCircle size={16} />
          </button>
        </Tooltip>

        <Tooltip
          position="top"
          content={
            <p className="text-[#8b949e]">
              Attach a file — shelf image, invoice, or audio (max 10MB)
            </p>
          }
        >
          <button
            onClick={() => toggleMode('file')}
            disabled={disabled}
            className={`p-1.5 rounded transition-colors shrink-0
                        disabled:opacity-30
                        ${mode === 'file'
                          ? 'text-[#58a6ff] bg-[#21262d]'
                          : 'text-[#8b949e] hover:text-[#e6edf3]'}
                        hover:bg-[#21262d]`}>
            <Paperclip size={16} />
          </button>
        </Tooltip>

        <Tooltip
          position="top"
          content={
            <p className="text-[#8b949e]">
              Record a voice command — speak, then click stop to send
            </p>
          }
        >
          <button
            onClick={() => toggleMode('voice')}
            disabled={disabled}
            className={`p-1.5 rounded transition-colors shrink-0
                        disabled:opacity-30
                        ${recording
                          ? 'text-[#f85149] bg-[#21262d]'
                          : mode === 'voice'
                            ? 'text-[#58a6ff] bg-[#21262d]'
                            : 'text-[#8b949e] hover:text-[#e6edf3]'}
                        hover:bg-[#21262d]`}>
            <Mic size={16} />
          </button>
        </Tooltip>

        <div className="w-px h-5 bg-[#30363d] shrink-0" />

        <input
          type="text"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled
            ? 'Awaiting PO decision...'
            : 'Type a command...'}
          className="flex-1 bg-transparent text-sm
                     text-[#e6edf3] placeholder-[#8b949e]
                     outline-none disabled:cursor-not-allowed
                     min-w-0"
        />

        {isLoading ? (
          <button
            onClick={onCancel}
            type="button"
            className="px-2.5 py-1 text-xs font-semibold rounded bg-[#da3633]
                       hover:bg-[#f85149] text-white transition-colors shrink-0 flex items-center gap-1 shadow"
          >
            <span>🛑</span> Cancel
          </button>
        ) : text.trim() ? (
          <button onClick={handleSend}
                  disabled={disabled}
                  className="p-1.5 rounded bg-[#238636]
                             hover:bg-[#2ea043] text-white
                             transition-colors shrink-0
                             disabled:opacity-30">
            <Send size={14} />
          </button>
        ) : null}
      </div>
    </div>
  )
}
