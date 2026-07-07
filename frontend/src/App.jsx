import { Routes, Route, NavLink } from 'react-router-dom'
import { Shield, GitPullRequest, Activity, Settings as SettingsIcon, RefreshCw } from 'lucide-react'
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
    { to: '/', icon: Activity, label: 'Dashboard' },
    { to: '/prs', icon: GitPullRequest, label: 'Pull Requests' },
    { to: '/settings', icon: SettingsIcon, label: 'Settings' },
  ]

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-dark-900 border-r border-dark-700 flex flex-col">
        <div className="p-6 border-b border-dark-700">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-emerald-400" />
            <div>
              <h1 className="text-lg font-bold text-dark-50">PR Review</h1>
              <p className="text-xs text-dark-400">Auto Security Scanner</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 font-medium'
                    : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-dark-700">
          <button
            onClick={triggerPoll}
            disabled={polling}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${polling ? 'animate-spin' : ''}`} />
            {polling ? 'Polling...' : 'Poll Now'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
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
