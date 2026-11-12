import { useState, useRef, useEffect, useCallback } from 'react'

export default function Tooltip({ children, content, position = 'top' }) {
  const [visible, setVisible] = useState(false)
  const ref = useRef(null)
  const hideTimer = useRef(null)

  const show = useCallback(() => {
    clearTimeout(hideTimer.current)
    setVisible(true)
  }, [])

  // 200ms grace period so mouse can travel from trigger → tooltip panel
  const hide = useCallback(() => {
    hideTimer.current = setTimeout(() => setVisible(false), 200)
  }, [])

  // Hide on outside click
  useEffect(() => {
    if (!visible) return
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        clearTimeout(hideTimer.current)
        setVisible(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [visible])

  // Cleanup timer on unmount
  useEffect(() => () => clearTimeout(hideTimer.current), [])

  return (
    <div ref={ref} className="relative inline-flex" style={{ zIndex: 50 }}>
      {/* Trigger */}
      <div onMouseEnter={show} onMouseLeave={hide}>
        {children}
      </div>

      {/* Invisible bridge fills the gap so mouse travel doesn't dismiss */}
      {visible && (
        <div
          className={`absolute left-0 w-full ${position === 'top' ? 'bottom-full h-3' : 'top-full h-3'}`}
          onMouseEnter={show}
          onMouseLeave={hide}
          aria-hidden="true"
        />
      )}

      {/* Tooltip panel */}
      {visible && (
        <div
          className={`absolute z-50 w-72 bg-[#161b22] border
                      border-[#30363d] rounded-lg shadow-xl p-3
                      text-xs text-[#e6edf3]
                      ${position === 'top'
                        ? 'bottom-full mb-3 left-0'
                        : 'top-full mt-3 left-0'}`}
          onMouseEnter={show}
          onMouseLeave={hide}
        >
          {content}
          {/* Arrow */}
          <div className={`absolute w-2 h-2 bg-[#161b22]
                           border-[#30363d] rotate-45
                           ${position === 'top'
                             ? 'border-b border-r -bottom-1 left-3'
                             : 'border-t border-l -top-1 left-3'}`}
          />
        </div>
      )}
    </div>
  )
}
