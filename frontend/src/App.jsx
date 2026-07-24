import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { Activity, GitPullRequest, LayoutDashboard, RefreshCw, Settings as SettingsIcon, Shield } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import PRList from './pages/PRList'
import PRDetail from './pages/PRDetail'
import SettingsPage from './pages/Settings'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Overview', code: '01' },
  { to: '/prs', icon: GitPullRequest, label: 'Signals', code: '02' },
  { to: '/settings', icon: SettingsIcon, label: 'Controls', code: '03' },
]

function App() {
  const [polling, setPolling] = useState(false)
  const [lastPulse, setLastPulse] = useState(null)
  const location = useLocation()

  const triggerPoll = async () => {
    setPolling(true)
    try {
      await fetch('/api/poll', { method: 'POST' })
      setLastPulse(new Date())
      setTimeout(() => setPolling(false), 5000)
    } catch (e) {
      console.error(e)
      setPolling(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="orbit-rail">
        <div className="flex h-full flex-col">
          <div>
            <div className="flex items-center gap-sm">
              <div className="living-orb" style={{ width: 44, height: 44 }} aria-hidden="true">
                <Shield className="w-5 h-5" style={{ color: 'var(--color-accent-ink)' }} />
              </div>
              <div>
                <p className="kicker">private orbit</p>
                <h1 style={{ color: 'var(--color-ink)', fontSize: 'var(--text-lg)', fontWeight: 800, letterSpacing: '-0.05em' }}>
                  Review Habitat
                </h1>
              </div>
            </div>

            <p style={{ marginTop: 'var(--space-lg)', color: 'var(--color-ink-3)', fontSize: 'var(--text-sm)', lineHeight: 1.7 }}>
              A living command room for Azure PR review, security signals, and inline comment operations.
            </p>
          </div>

          <nav style={{ display: 'grid', gap: 'var(--space-xs)', marginTop: 'var(--space-2xl)' }} aria-label="Primary">
            {navItems.map(({ to, icon: Icon, label, code }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                style={({ isActive }) => ({
                  display: 'grid',
                  gridTemplateColumns: '2.25rem minmax(0, 1fr) auto',
                  alignItems: 'center',
                  gap: 'var(--space-xs)',
                  minHeight: 48,
                  padding: 'var(--space-xs)',
                  borderRadius: 'var(--radius-lg)',
                  border: `1px solid ${isActive ? 'var(--color-rule-living)' : 'transparent'}`,
                  background: isActive ? 'var(--color-accent-bg)' : 'transparent',
                  color: isActive ? 'var(--color-ink)' : 'var(--color-ink-3)',
                  textDecoration: 'none',
                  transition: `background var(--dur-short) var(--ease-out), border-color var(--dur-short) var(--ease-out), color var(--dur-short) var(--ease-out)`,
                })}
              >
                {({ isActive }) => (
                  <>
                    <span
                      className="mono"
                      style={{
                        display: 'grid',
                        placeItems: 'center',
                        width: 34,
                        height: 34,
                        borderRadius: 'var(--radius-md)',
                        background: isActive ? 'var(--color-accent)' : 'var(--color-paper-3)',
                        color: isActive ? 'var(--color-accent-ink)' : 'var(--color-ink-4)',
                        fontSize: 'var(--text-xs)',
                        fontWeight: 700,
                      }}
                    >
                      {code}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', fontWeight: 700, whiteSpace: 'nowrap' }}>
                      <Icon className="w-4 h-4" style={{ color: isActive ? 'var(--color-accent)' : 'var(--color-ink-4)' }} />
                      {label}
                    </span>
                    {isActive && <span className="signal-dot" aria-hidden="true" />}
                  </>
                )}
              </NavLink>
            ))}
          </nav>

          <div style={{ marginTop: 'auto' }}>
            <div className="panel-soft" style={{ padding: 'var(--space-md)', marginBottom: 'var(--space-sm)' }}>
              <div className="flex items-center justify-between gap-sm">
                <div className="flex items-center gap-xs">
                  <Activity className="w-4 h-4" style={{ color: polling ? 'var(--color-accent)' : 'var(--color-ink-4)' }} />
                  <span className="mono" style={{ color: 'var(--color-ink-3)', fontSize: 'var(--text-xs)' }}>
                    {polling ? 'polling now' : 'orbit idle'}
                  </span>
                </div>
                <span className={`signal-dot ${polling ? 'is-running' : ''}`} aria-hidden="true" />
              </div>
              <p className="mono" style={{ marginTop: 'var(--space-xs)', color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)' }}>
                {lastPulse ? lastPulse.toLocaleTimeString('th-TH') : location.pathname === '/' ? 'ready' : 'standing by'}
              </p>
            </div>

            <button
              onClick={triggerPoll}
              disabled={polling}
              style={{
                width: '100%',
                minHeight: 48,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-xs)',
                border: '1px solid var(--color-rule-living)',
                borderRadius: 'var(--radius-lg)',
                background: polling ? 'var(--color-accent-bg)' : 'var(--color-accent)',
                color: polling ? 'var(--color-accent)' : 'var(--color-accent-ink)',
                fontWeight: 800,
                whiteSpace: 'nowrap',
                transition: `background var(--dur-short) var(--ease-out), color var(--dur-short) var(--ease-out)`,
              }}
            >
              <RefreshCw className="w-4 h-4" style={polling ? { animation: 'orbit-turn 1.2s linear infinite' } : {}} />
              {polling ? 'Polling' : 'Poll now'}
            </button>
          </div>
        </div>
      </aside>

      <main className="orbit-main">
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
