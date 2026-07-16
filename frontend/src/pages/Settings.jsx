/* Hallmark · genre: atmospheric · macrostructure: Workbench · design-system: design.md · designed-as-app */

import { useState, useEffect } from 'react'
import {
  Play, Pause, Clock, RefreshCw,
  CheckCircle, XCircle, MessageSquare, Loader2, Info, AlertTriangle
} from 'lucide-react'

/* ── Card base ───────────────────────────────────────────────────── */

const cardStyle = {
  background: 'var(--color-paper-2)',
  border: '1px solid var(--color-rule)',
  borderRadius: 'var(--radius-lg)',
  overflow: 'hidden',
}

const sectionLabel = {
  fontSize: 'var(--text-xs)',
  fontWeight: 600,
  color: 'var(--color-ink-3)',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  fontFamily: 'var(--font-mono)',
}

/* ── Loading skeleton ────────────────────────────────────────────── */

function LoadingSkeleton() {
  return (
    <div className="p-lg space-y-md animate-fade-in" style={{ maxWidth: 640 }}>
      <div className="space-y-2xs">
        <div className="skeleton" style={{ height: 28, width: 180 }} />
        <div className="skeleton" style={{ height: 16, width: 240 }} />
      </div>
      <div style={{ ...cardStyle, padding: 'var(--space-lg)' }}>
        <div className="skeleton" style={{ height: 200 }} />
      </div>
      <div style={{ ...cardStyle, padding: 'var(--space-lg)' }}>
        <div className="skeleton" style={{ height: 140 }} />
      </div>
    </div>
  )
}

/* ── Toggle switch (8 states) ────────────────────────────────────── */

function Toggle({ enabled, onChange, loading }) {
  return (
    <button
      onClick={onChange}
      disabled={loading}
      className="relative inline-flex items-center"
      style={{
        height: 24,
        width: 44,
        borderRadius: 'var(--radius-full)',
        background: enabled ? 'var(--color-accent)' : 'var(--color-paper-4)',
        border: 'none',
        cursor: loading ? 'not-allowed' : 'pointer',
        opacity: loading ? 0.5 : 1,
        transition: `background var(--dur-short) var(--ease-out)`,
        padding: 0,
      }}
    >
      <span
        style={{
          display: 'inline-block',
          height: 16,
          width: 16,
          borderRadius: 'var(--radius-full)',
          background: 'var(--color-ink)',
          boxShadow: '0 1px 3px oklch(10% 0.01 260 / 0.3)',
          transform: enabled ? 'translateX(24px)' : 'translateX(4px)',
          transition: `transform var(--dur-short) var(--ease-out)`,
        }}
      />
    </button>
  )
}

/* ── Settings page ───────────────────────────────────────────────── */

function SettingsPage() {
  const [status, setStatus] = useState(null)
  const [interval, setIntervalState] = useState(10)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState('')
  const [message, setMessage] = useState(null)
  const [autoComment, setAutoComment] = useState(false)
  const [autoCommentLoading, setAutoCommentLoading] = useState(false)

  const fetchStatus = async () => {
    try {
      const resp = await fetch('/api/scheduler/status')
      const data = await resp.json()
      setStatus(data)
      setIntervalState(data.interval_minutes)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const fetchAutoComment = async () => {
    try {
      const resp = await fetch('/api/settings/auto-comment')
      const data = await resp.json()
      setAutoComment(data.enabled)
    } catch (e) {
      console.error(e)
    }
  }

  const toggleAutoComment = async () => {
    setAutoCommentLoading(true)
    setMessage(null)
    try {
      const endpoint = autoComment
        ? '/api/settings/auto-comment/disable'
        : '/api/settings/auto-comment/enable'
      const resp = await fetch(endpoint, { method: 'POST' })
      const data = await resp.json()
      setAutoComment(!autoComment)
      showMessage('success', data.message)
    } catch (e) {
      showMessage('error', 'Failed to toggle auto-comment')
    } finally {
      setAutoCommentLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    fetchAutoComment()
    const timer = setInterval(fetchStatus, 5000)
    return () => clearInterval(timer)
  }, [])

  const showMessage = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 4000)
  }

  const toggleScheduler = async () => {
    if (!status) return
    setActionLoading(status.enabled ? 'disable' : 'enable')
    setMessage(null)

    try {
      const endpoint = status.enabled ? '/api/scheduler/disable' : '/api/scheduler/enable'
      const resp = await fetch(endpoint, { method: 'POST' })
      const data = await resp.json()

      if (data.status === 'enabled' || data.status === 'disabled' || data.status === 'already_enabled' || data.status === 'already_disabled') {
        showMessage('success', data.message || `Poller ${data.status}`)
      } else {
        showMessage('error', data.detail || 'Unknown error')
      }

      await fetchStatus()
    } catch (e) {
      showMessage('error', 'Failed to toggle poller')
    } finally {
      setActionLoading('')
    }
  }

  const updateInterval = async () => {
    setActionLoading('interval')
    setMessage(null)

    try {
      const resp = await fetch('/api/scheduler/interval', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ minutes: interval }),
      })
      const data = await resp.json()

      if (data.status === 'updated') {
        showMessage('success', `Interval updated to ${interval} minutes`)
      } else {
        showMessage('error', data.detail || 'Failed to update')
      }

      await fetchStatus()
    } catch (e) {
      showMessage('error', 'Failed to update interval')
    } finally {
      setActionLoading('')
    }
  }

  if (loading) return <LoadingSkeleton />

  const btnPrimary = {
    background: 'var(--color-accent)',
    color: 'var(--color-accent-ink)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    padding: '12px 20px',
    fontSize: 'var(--text-base)',
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    fontFamily: 'var(--font-body)',
    transition: `all var(--dur-short) var(--ease-out)`,
  }

  const btnDanger = {
    ...btnPrimary,
    background: 'var(--color-danger)',
  }

  const btnSecondary = {
    background: 'var(--color-info)',
    color: 'oklch(14% 0.04 250)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    padding: '10px 20px',
    fontSize: 'var(--text-sm)',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontFamily: 'var(--font-body)',
    transition: `all var(--dur-short) var(--ease-out)`,
  }

  const presetBase = {
    padding: '6px 12px',
    borderRadius: 'var(--radius-md)',
    fontSize: 'var(--text-xs)',
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    fontFamily: 'var(--font-mono)',
    transition: `all var(--dur-micro) var(--ease-out)`,
  }

  const infoBox = {
    background: 'var(--color-paper-3)',
    border: '1px solid var(--color-rule)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-sm) var(--space-md)',
  }

  return (
    <div className="p-lg space-y-md animate-fade-in" style={{ maxWidth: 640 }}>
      {/* Header */}
      <div>
        <h2 className="font-semibold tracking-tight" style={{ fontSize: 'var(--text-xl)', color: 'var(--color-ink)', letterSpacing: '-0.025em' }}>
          Settings
        </h2>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)', marginTop: 4 }}>
          Manage the automated review system
        </p>
      </div>

      {/* System Status */}
      <div style={cardStyle}>
        <div className="px-md py-sm border-b" style={{ borderColor: 'var(--color-rule)' }}>
          <h3 style={sectionLabel}>System Status</h3>
        </div>
        <div className="p-md space-y-md">
          {/* Status indicator */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-sm">
              <span className="relative flex" style={{ width: 10, height: 10 }}>
                {status?.enabled && (
                  <span
                    className="absolute inline-flex h-full w-full rounded-full"
                    style={{
                      background: 'var(--color-accent)',
                      opacity: 0.5,
                      animation: 'ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite',
                    }}
                  />
                )}
                <span
                  className="relative inline-flex rounded-full"
                  style={{
                    width: 10,
                    height: 10,
                    background: status?.enabled ? 'var(--color-accent)' : 'var(--color-ink-4)',
                  }}
                />
              </span>
              <span className="font-medium" style={{ fontSize: 'var(--text-base)', color: 'var(--color-ink-2)' }}>
                {status?.enabled ? 'Running' : 'Stopped'}
              </span>
            </div>
            <span className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)' }}>
              Scheduler: {status?.scheduler_running ? 'active' : 'inactive'}
            </span>
          </div>

          {/* Info grid */}
          <div className="grid grid-cols-2 gap-xs">
            <div style={infoBox}>
              <p className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                Poll Interval
              </p>
              <p className="font-bold font-mono" style={{ fontSize: 'var(--text-xl)', color: 'var(--color-ink)' }}>
                {status?.interval_minutes} <span style={{ fontSize: 'var(--text-sm)', fontWeight: 400, color: 'var(--color-ink-3)' }}>min</span>
              </p>
            </div>
            <div style={infoBox}>
              <p className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
                Next Run
              </p>
              <p className="font-medium" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>
                {status?.next_run
                  ? new Date(status.next_run).toLocaleString('th-TH')
                  : '— (paused)'}
              </p>
            </div>
          </div>

          {/* Toggle button */}
          <button
            onClick={toggleScheduler}
            disabled={!!actionLoading}
            style={{
              ...(status?.enabled ? btnDanger : btnPrimary),
              opacity: actionLoading ? 0.6 : 1,
              cursor: actionLoading ? 'not-allowed' : 'pointer',
            }}
          >
            {actionLoading === 'enable' || actionLoading === 'disable' ? (
              <>
                <Loader2 className="w-4 h-4" style={{ animation: 'spin 1s linear infinite' }} />
                Processing...
              </>
            ) : status?.enabled ? (
              <>
                <Pause className="w-4 h-4" />
                Stop Poller
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Start Poller
              </>
            )}
          </button>
        </div>
      </div>

      {/* Interval Settings */}
      <div style={cardStyle}>
        <div className="px-md py-sm border-b" style={{ borderColor: 'var(--color-rule)' }}>
          <h3 style={sectionLabel}>Poll Interval</h3>
        </div>
        <div className="p-md space-y-md">
          <div>
            <label className="block" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)', marginBottom: 8 }}>
              Frequency (minutes)
            </label>
            <div className="flex items-center gap-sm">
              <input
                type="number"
                min={1}
                max={1440}
                value={interval}
                onChange={e => setIntervalState(parseInt(e.target.value) || 1)}
                className="font-mono"
                style={{
                  width: 100,
                  background: 'var(--color-paper-3)',
                  border: '1px solid var(--color-rule)',
                  color: 'var(--color-ink)',
                  fontSize: 'var(--text-md)',
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 14px',
                  outline: 'none',
                  fontFamily: 'var(--font-mono)',
                  transition: `border-color var(--dur-micro) var(--ease-out)`,
                }}
                onFocus={e => e.currentTarget.style.borderColor = 'var(--color-focus)'}
                onBlur={e => e.currentTarget.style.borderColor = 'var(--color-rule)'}
              />
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-4)' }}>minutes</span>
            </div>
            <p className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)', marginTop: 6 }}>
              1 – 1,440 minutes (max 24 hours)
            </p>
          </div>

          {/* Presets */}
          <div className="flex gap-2xs">
            {[5, 10, 15, 30, 60].map(m => (
              <button
                key={m}
                onClick={() => setIntervalState(m)}
                style={{
                  ...presetBase,
                  background: interval === m ? 'var(--color-accent)' : 'var(--color-paper-3)',
                  color: interval === m ? 'var(--color-accent-ink)' : 'var(--color-ink-3)',
                  border: interval === m ? 'none' : '1px solid var(--color-rule)',
                }}
              >
                {m}m
              </button>
            ))}
          </div>

          <button
            onClick={updateInterval}
            disabled={!!actionLoading || interval === status?.interval_minutes}
            style={{
              ...btnSecondary,
              opacity: actionLoading || interval === status?.interval_minutes ? 0.4 : 1,
              cursor: actionLoading || interval === status?.interval_minutes ? 'not-allowed' : 'pointer',
            }}
          >
            {actionLoading === 'interval' ? (
              <>
                <Loader2 className="w-4 h-4" style={{ animation: 'spin 1s linear infinite' }} />
                Updating...
              </>
            ) : (
              <>
                <Clock className="w-4 h-4" />
                Update Interval
              </>
            )}
          </button>
        </div>
      </div>

      {/* Auto-Comment */}
      <div style={cardStyle}>
        <div className="px-md py-sm border-b" style={{ borderColor: 'var(--color-rule)' }}>
          <h3 style={sectionLabel}>Auto-Comment</h3>
        </div>
        <div className="p-md space-y-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium" style={{ fontSize: 'var(--text-base)', color: 'var(--color-ink-2)' }}>
                Post comments on Azure DevOps
              </p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)', marginTop: 2 }}>
                Automatically comment review results on PRs after completion
              </p>
            </div>
            <Toggle enabled={autoComment} onChange={toggleAutoComment} loading={autoCommentLoading} />
          </div>

          {autoComment && (
            <div className="animate-slide-down" style={infoBox}>
              <div className="flex items-center gap-2xs" style={{ marginBottom: 'var(--space-sm)' }}>
                <Info className="w-4 h-4" style={{ color: 'var(--color-info)' }} />
                <p className="font-medium" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>
                  When a review completes, the system will:
                </p>
              </div>
              <ul style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>
                <li className="flex items-start gap-2xs">
                  <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--color-ink-4)', marginTop: 2 }} />
                  <span>Post a <strong style={{ color: 'var(--color-ink)' }}>summary comment</strong> on the PR thread (scores + recommendation)</span>
                </li>
                <li className="flex items-start gap-2xs">
                  <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--color-warning)', marginTop: 2 }} />
                  <span>Post <strong style={{ color: 'var(--color-ink)' }}>inline comments</strong> on lines with HIGH/MEDIUM findings</span>
                </li>
                <li className="flex items-start gap-2xs">
                  <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--color-success)', marginTop: 2 }} />
                  <span>Include <strong style={{ color: 'var(--color-ink)' }}>fix suggestions</strong> in every comment</span>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Toast message */}
      {message && (
        <div
          className="fixed flex items-center gap-sm"
          style={{
            bottom: 24,
            right: 24,
            padding: '12px 16px',
            borderRadius: 'var(--radius-lg)',
            boxShadow: '0 4px 12px oklch(10% 0.01 260 / 0.4)',
            border: `1px solid ${message.type === 'success' ? 'var(--color-success)' : 'var(--color-danger)'}`,
            background: message.type === 'success' ? 'var(--color-success-bg)' : 'var(--color-danger-bg)',
            color: message.type === 'success' ? 'var(--color-success)' : 'var(--color-danger)',
            fontSize: 'var(--text-sm)',
            animation: 'slideUp var(--dur-long) var(--ease-out)',
            zIndex: 'var(--z-toast)',
          }}
        >
          {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {message.text}
        </div>
      )}
    </div>
  )
}

export default SettingsPage
