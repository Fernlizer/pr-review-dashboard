import { Routes, Route, NavLink } from 'react-router-dom'
import { Shield, GitPullRequest, LayoutDashboard, Settings as SettingsIcon, RefreshCw } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import PRList from './pages/PRList'
import PRDetail from './pages/PRDetail'
import SettingsPage from './pages/Settings'
import { useState } from 'react'

function App() {
  const [polling, setPolling] = useState(false)

  const triggerPoll = async () => {
    setPolling(true)
    try {
      await fetch('/api/poll', { method: 'POST' })
      window.location.reload()
    } catch (e) {
      console.error(e)
    } finally {
      setPolling(false)
    }
  }

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/prs', icon: GitPullRequest, label: 'Pull Requests' },
    { to: '/settings', icon: SettingsIcon, label: 'Settings' },
  ]

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-[260px] bg-surface border-r border-surface-border flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 flex items-center justify-center">
              <Shield className="w-4.5 h-4.5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-[15px] font-semibold text-dark-100 tracking-tight">PR Review</h1>
              <p className="text-[11px] text-dark-500 leading-tight">Security Scanner</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `group flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-dark-800 text-dark-50'
                    : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800/50'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-emerald-400' : 'text-dark-500 group-hover:text-dark-400'}`} />
                  {label}
                  {isActive && (
                    <div className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Poll button */}
        <div className="p-3 border-t border-surface-border">
          <button
            onClick={triggerPoll}
            disabled={polling}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-[13px] font-medium transition-all duration-150 active:scale-[0.98]"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${polling ? 'animate-spin' : ''}`} />
            {polling ? 'Polling...' : 'Poll Now'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto min-w-0">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/prs" element={<PRList />} />
          <Route path="/prs/:id" element={<PRDetail />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
