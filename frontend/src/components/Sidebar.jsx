import React, { useState } from 'react'
import { getHealth } from '../api/client'
import { KeyRound, LogOut, User, CheckSquare } from 'lucide-react'

export default function Sidebar({ devMode, adminMode, role, onRoleChange, activePage, onNavigate }) {
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState(false)

  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    setLoginError(false)
    try {
      const health = await getHealth()
      const expectedPassword = health.manager_password || 'sovereign'
      if (password === expectedPassword) {
        onRoleChange('manager')
        onNavigate('manager')
        setShowLoginModal(false)
        setPassword('')
      } else {
        setLoginError(true)
      }
    } catch {
      if (password === 'sovereign') {
        onRoleChange('manager')
        onNavigate('manager')
        setShowLoginModal(false)
        setPassword('')
      } else {
        setLoginError(true)
      }
    }
  }

  const handleLogout = () => {
    onRoleChange('operator')
    if (activePage === 'manager') {
      onNavigate('orchestrator')
    }
  }

  return (
    <aside className="w-48 bg-[#0d1117] border-r border-[#30363d] flex flex-col py-4 px-3 shrink-0 h-screen sticky top-0 justify-between">
      <div>
        {/* Brand / Logo */}
        <div className="flex items-center gap-2 mb-6 px-1">
          <span className="text-xl" title="Sovereign Supply Chain">
            🛡️
          </span>
          <span className="font-semibold text-xs tracking-wider uppercase text-[#e6edf3]">
            Sovereign
          </span>
        </div>

        {/* Navigation links */}
        <div className="space-y-1">
          <button
            onClick={() => onNavigate('orchestrator')}
            className={`w-full text-left px-2.5 py-1.5 rounded text-xs flex items-center gap-2 transition-colors ${
              activePage === 'orchestrator'
                ? 'bg-[#21262d] text-[#58a6ff] font-semibold'
                : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#161b22]'
            }`}
          >
            <span>⚡</span> Orchestrator
          </button>

          <button
            onClick={() => onNavigate('analytics')}
            className={`w-full text-left px-2.5 py-1.5 rounded text-xs flex items-center gap-2 transition-colors ${
              activePage === 'analytics'
                ? 'bg-[#21262d] text-[#58a6ff] font-semibold'
                : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#161b22]'
            }`}
          >
            <span>📊</span> Analytics
          </button>

          {role === 'manager' && (
            <button
              onClick={() => onNavigate('manager')}
              className={`w-full text-left px-2.5 py-1.5 rounded text-xs flex items-center gap-2 transition-colors ${
                activePage === 'manager'
                  ? 'bg-[#21262d] text-[#58a6ff] font-semibold'
                  : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#161b22]'
              }`}
            >
              <CheckSquare size={13} /> Manager Approvals
            </button>
          )}
        </div>
      </div>

      {/* Role and Auth Controls */}
      <div className="border-t border-[#30363d] pt-3 space-y-2">
        {role === 'manager' ? (
          <div className="space-y-1">
            <div className="text-xs text-[#3fb950] font-semibold flex items-center gap-1.5 px-2">
              <KeyRound size={13} /> Manager
            </div>
            <button
              onClick={handleLogout}
              className="w-full text-left px-2 py-1 text-xs text-[#f85149] hover:bg-[#21262d] rounded flex items-center gap-1.5 transition-colors"
            >
              <LogOut size={13} /> Log Out
            </button>
          </div>
        ) : (
          <div className="space-y-1.5">
            <div className="text-xs text-[#8b949e] flex items-center gap-1.5 px-2">
              <User size={13} /> Operator
            </div>
            {!showLoginModal ? (
              <button
                onClick={() => setShowLoginModal(true)}
                className="w-full text-left px-2 py-1 text-xs text-[#58a6ff] hover:bg-[#21262d] rounded flex items-center gap-1.5 transition-colors"
              >
                <KeyRound size={13} /> Manager Login
              </button>
            ) : (
              <form onSubmit={handleLoginSubmit} className="space-y-1.5 px-1">
                <input
                  type="password"
                  placeholder="Manager key..."
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full bg-[#161b22] border border-[#30363d] rounded px-2 py-1 text-xs text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
                  autoFocus
                />
                {loginError && (
                  <div className="text-[11px] text-[#f85149]">
                    ⚠️ Incorrect access key
                  </div>
                )}
                <div className="flex gap-1 pt-1">
                  <button
                    type="submit"
                    className="flex-1 bg-[#238636] hover:bg-[#2ea043] text-white py-0.5 rounded text-[11px] font-medium"
                  >
                    Submit Key
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setShowLoginModal(false)
                      setLoginError(false)
                    }}
                    className="px-2 text-[11px] text-[#8b949e] hover:text-[#e6edf3]"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {devMode && (
          <div className="text-[10px] text-[#8b949e] uppercase font-mono px-2 pt-2 border-t border-[#30363d]">
            DEV MODE
          </div>
        )}
      </div>
    </aside>
  )
}
