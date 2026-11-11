import React, { useState, useEffect } from 'react'
import { loginManager } from '../api/client'
import { KeyRound, LogOut, CheckSquare, ChevronLeft, ChevronRight } from 'lucide-react'

export default function Sidebar({ devMode, adminMode, role, onRoleChange, activePage, onNavigate }) {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem('sidebar_collapsed') === 'true'
  })

  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', collapsed ? 'true' : 'false')
  }, [collapsed])

  const handleManagerLogin = async () => {
    try {
      const res = await loginManager()
      if (res.role === 'manager') {
        onRoleChange('manager')
        onNavigate('manager')
      }
    } catch {
      // Direct local fallback if offline/mock
      onRoleChange('manager')
      onNavigate('manager')
    }
  }

  const handleLogout = () => {
    onRoleChange('operator')
    if (activePage === 'manager') {
      onNavigate('orchestrator')
    }
  }

  const toggleCollapse = () => {
    setCollapsed(prev => !prev)
  }

  return (
    <aside
      className={`${
        collapsed ? 'w-12 px-1' : 'w-48 px-3'
      } bg-[#0d1117] border-r border-[#30363d] flex flex-col py-4 shrink-0 h-screen sticky top-0 justify-between transition-all duration-200 select-none`}
    >
      <div>
        {/* Brand / Logo */}
        <div
          className={`flex items-center gap-2 mb-6 ${
            collapsed ? 'justify-center px-0' : 'px-1'
          }`}
          title="Sovereign Supply Chain"
        >
          <span className="text-xl">
            🛡️
          </span>
          {!collapsed && (
            <span className="font-semibold text-xs tracking-wider uppercase text-[#e6edf3]">
              Sovereign
            </span>
          )}
        </div>

        {/* Navigation links */}
        <div className="space-y-1">
          <button
            onClick={() => onNavigate('orchestrator')}
            title="Orchestrator"
            className={`w-full text-left py-1.5 rounded text-xs flex items-center transition-colors ${
              collapsed ? 'justify-center px-1' : 'px-2.5 gap-2'
            } ${
              activePage === 'orchestrator'
                ? 'bg-[#21262d] text-[#58a6ff] font-semibold'
                : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#161b22]'
            }`}
          >
            <span className="text-sm leading-none">⚡</span>
            {!collapsed && <span>Orchestrator</span>}
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
              title="Manager Approvals"
              className={`w-full text-left py-1.5 rounded text-xs flex items-center transition-colors ${
                collapsed ? 'justify-center px-1' : 'px-2.5 gap-2'
              } ${
                activePage === 'manager'
                  ? 'bg-[#21262d] text-[#58a6ff] font-semibold'
                  : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#161b22]'
              }`}
            >
              <CheckSquare size={14} className="shrink-0" />
              {!collapsed && <span>Manager Approvals</span>}
            </button>
          )}
        </div>
      </div>

      {/* Role, Auth Controls & Collapse Toggle */}
      <div className="border-t border-[#30363d] pt-3 space-y-2">
        {role === 'manager' ? (
          <div className="space-y-1">
            {!collapsed ? (
              <div className="text-xs text-[#3fb950] font-semibold flex items-center gap-1.5 px-2">
                <KeyRound size={13} /> Manager
              </div>
            ) : (
              <div
                title="Manager Role Active"
                className="flex justify-center text-[#3fb950] py-1"
              >
                <KeyRound size={14} />
              </div>
            )}
            <button
              onClick={handleLogout}
              title="Log Out"
              className={`w-full text-left py-1 text-xs text-[#f85149] hover:bg-[#21262d] rounded flex items-center transition-colors ${
                collapsed ? 'justify-center px-1' : 'px-2 gap-1.5'
              }`}
            >
              <LogOut size={13} className="shrink-0" />
              {!collapsed && <span>Log Out</span>}
            </button>
          </div>
        ) : (
          <div>
            <button
              onClick={handleManagerLogin}
              title="Manager Login"
              className={`w-full text-left py-1.5 text-xs text-[#58a6ff] hover:bg-[#21262d] rounded flex items-center transition-colors ${
                collapsed ? 'justify-center px-1' : 'px-2 gap-1.5'
              }`}
            >
              <KeyRound size={13} className="shrink-0" />
              {!collapsed && <span>Manager Login</span>}
            </button>
          </div>
        )}

        {devMode && !collapsed && (
          <div className="text-[10px] text-[#8b949e] uppercase font-mono px-2 pt-1 border-t border-[#30363d]">
            DEV MODE
          </div>
        )}

        {/* Collapse / Expand Toggle Button at Bottom */}
        <div className="pt-2 border-t border-[#30363d]">
          <button
            onClick={toggleCollapse}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={`w-full py-1 text-xs text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d] rounded flex items-center transition-colors ${
              collapsed ? 'justify-center' : 'px-2 gap-1.5'
            }`}
          >
            {collapsed ? (
              <>
                <ChevronRight size={14} />
                <span className="sr-only">»</span>
              </>
            ) : (
              <>
                <ChevronLeft size={14} />
                <span>« Collapse</span>
              </>
            )}
          </button>
        </div>
      </div>
    </aside>
  )
}
