import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import Orchestrator from './pages/Orchestrator'
import ManagerApprovals from './pages/ManagerApprovals'

const params = new URLSearchParams(window.location.search)
const devMode = params.get('dev') === '1'
const adminMode = params.get('admin') === '1'

export default function App() {
  const [role, setRole] = useState('operator')
  const [activePage, setActivePage] = useState('orchestrator')

  return (
    <div className="flex h-screen bg-[#0d1117] text-[#e6edf3] overflow-hidden">
      <Sidebar
        devMode={devMode}
        adminMode={adminMode}
        role={role}
        onRoleChange={setRole}
        activePage={activePage}
        onNavigate={setActivePage}
      />
      <main className="flex-1 overflow-y-auto">
        {activePage === 'manager' && role === 'manager' ? (
          <ManagerApprovals />
        ) : (
          <Orchestrator />
        )}
      </main>
    </div>
  )
}
