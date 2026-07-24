/* Hallmark · pre-emit critique: P4 H5 E4 S5 R4 V5 */
/* Hallmark · genre: atmospheric · macrostructure: Control Room · theme: custom Night Garden */

import { useEffect, useState } from 'react'
import { CheckCircle, Clock, Loader2, MessageSquare, Pause, Play, RefreshCw, Settings2, ShieldCheck, XCircle } from 'lucide-react'

function LoadingSkeleton() {
  return (
    <div className="page-frame" style={{ display: 'grid', gap: 'var(--space-md)' }}>
      <div className="skeleton" style={{ height: 180 }} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-md">
        <div className="skeleton" style={{ height: 320 }} />
        <div className="skeleton" style={{ height: 320 }} />
      </div>
    </div>
  )
}

function Toggle({ enabled, onChange, loading }) {
  return (
    <button
      onClick={onChange}
      disabled={loading}
      aria-pressed={enabled}
      style={{
        width: 58,
        height: 32,
        border: `1px solid ${enabled ? 'var(--color-rule-living)' : 'var(--color-rule)'}`,
        borderRadius: 'var(--radius-full)',
        background: enabled ? 'var(--color-accent-bg)' : 'var(--color-paper-3)',
        padding: 4,
        transition: `background var(--dur-short) var(--ease-out), border-color var(--dur-short) var(--ease-out)`,
      }}
    >
      <span
        style={{
          display: 'block',
          width: 22,
          height: 22,
          borderRadius: 'var(--radius-full)',
          background: enabled ? 'var(--color-accent)' : 'var(--color-ink-4)',
          transform: enabled ? 'translateX(26px)' : 'translateX(0)',
          transition: `transform var(--dur-short) var(--ease-out), background var(--dur-short) var(--ease-out)`,
        }}
      />
    </button>
  )
}

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
    } finally {
      setLoading(false)
    }
  }

  const fetchAutoComment = async () => {
    const resp = await fetch('/api/settings/auto-comment')
    const data = await resp.json()
    setAutoComment(data.enabled)
  }

  useEffect(() => {
    fetchStatus()
    fetchAutoComment().catch(console.error)
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
      showMessage(resp.ok ? 'success' : 'error', data.message || data.detail || 'Scheduler changed')
      await fetchStatus()
    } catch {
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
      showMessage(resp.ok ? 'success' : 'error', data.message || data.detail || `Interval updated to ${interval} minutes`)
      await fetchStatus()
    } catch {
      showMessage('error', 'Failed to update interval')
    } finally {
      setActionLoading('')
    }
  }

  const toggleAutoComment = async () => {
    setAutoCommentLoading(true)
    setMessage(null)
    try {
      const endpoint = autoComment ? '/api/settings/auto-comment/disable' : '/api/settings/auto-comment/enable'
      const resp = await fetch(endpoint, { method: 'POST' })
      const data = await resp.json()
      if (resp.ok) setAutoComment(!autoComment)
      showMessage(resp.ok ? 'success' : 'error', data.message || data.detail || 'Auto-comment changed')
    } catch {
      showMessage('error', 'Failed to toggle auto-comment')
    } finally {
      setAutoCommentLoading(false)
    }
  }

  if (loading) return <LoadingSkeleton />

  const enabled = !!status?.enabled

  return (
    <div className="page-frame" style={{ display: 'grid', gap: 'var(--space-lg)' }}>
      <section className={`panel ${enabled ? 'panel-live' : ''} reveal`} style={{ padding: 'var(--space-xl)' }}>
        <div className="flex items-start justify-between gap-lg flex-wrap">
          <div>
            <p className="kicker">control room</p>
            <h1 className="display-title" style={{ marginTop: 'var(--space-sm)' }}>
              Tune the habitat.
            </h1>
            <p style={{ maxWidth: '62ch', marginTop: 'var(--space-md)', color: 'var(--color-ink-2)', fontSize: 'var(--text-md)', lineHeight: 1.75 }}>
              Scheduler cadence, review polling, and Azure DevOps comments stay here: close enough to touch, quiet enough to trust.
            </p>
          </div>
          <div className="living-orb" style={{ width: 160, height: 160 }}>
            <div style={{ textAlign: 'center' }}>
              <Settings2 className="w-7 h-7 mx-auto" style={{ color: enabled ? 'var(--color-accent)' : 'var(--color-ink-4)' }} />
              <p className="mono" style={{ marginTop: 'var(--space-md)', color: enabled ? 'var(--color-accent)' : 'var(--color-ink-4)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.12em', fontSize: 'var(--text-xs)' }}>
                {enabled ? 'poller live' : 'poller paused'}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[1.1fr_0.9fr] gap-md">
        <div className="panel reveal" style={{ padding: 'var(--space-lg)' }}>
          <div className="flex items-center justify-between gap-md">
            <div>
              <p className="kicker">scheduler pulse</p>
              <h2 style={{ color: 'var(--color-ink)', fontSize: 'var(--text-xl)', fontWeight: 800, letterSpacing: '-0.04em', marginTop: 'var(--space-xs)' }}>
                {enabled ? 'Active poll cycle' : 'Manual control'}
              </h2>
            </div>
            <span className={`signal-dot ${enabled ? 'is-running' : ''}`} aria-hidden="true" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-sm" style={{ marginTop: 'var(--space-lg)' }}>
            <InfoTile label="interval" value={`${status?.interval_minutes || interval} min`} />
            <InfoTile label="next run" value={status?.next_run ? new Date(status.next_run).toLocaleString('th-TH') : 'paused'} />
          </div>

          <button
            onClick={toggleScheduler}
            disabled={!!actionLoading}
            style={{
              ...primaryButton,
              width: '100%',
              marginTop: 'var(--space-lg)',
              background: enabled ? 'var(--color-danger)' : 'var(--color-accent)',
              color: enabled ? 'var(--color-ink)' : 'var(--color-accent-ink)',
            }}
          >
            {actionLoading ? <Loader2 className="w-4 h-4" style={{ animation: 'orbit-turn 1.2s linear infinite' }} /> : enabled ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {enabled ? 'Stop poller' : 'Start poller'}
          </button>
        </div>

        <div className="panel reveal" style={{ padding: 'var(--space-lg)' }}>
          <p className="kicker">cadence</p>
          <label style={{ display: 'block', marginTop: 'var(--space-lg)', color: 'var(--color-ink-3)', fontSize: 'var(--text-sm)' }}>
            Frequency in minutes
          </label>
          <div className="flex items-center gap-sm" style={{ marginTop: 'var(--space-xs)' }}>
            <input
              type="number"
              min={1}
              max={1440}
              value={interval}
              onChange={e => setIntervalState(parseInt(e.target.value) || 1)}
              className="mono"
              style={{
                minHeight: 48,
                width: 120,
                border: '1px solid var(--color-rule)',
                borderRadius: 'var(--radius-input)',
                background: 'var(--color-paper)',
                color: 'var(--color-ink)',
                padding: '0 var(--space-md)',
              }}
            />
            <button onClick={updateInterval} disabled={!!actionLoading || interval === status?.interval_minutes} style={secondaryButton}>
              {actionLoading === 'interval' ? <Loader2 className="w-4 h-4" style={{ animation: 'orbit-turn 1.2s linear infinite' }} /> : <Clock className="w-4 h-4" />}
              update
            </button>
          </div>
          <div className="flex gap-xs flex-wrap" style={{ marginTop: 'var(--space-md)' }}>
            {[5, 10, 15, 30, 60].map(m => (
              <button
                key={m}
                onClick={() => setIntervalState(m)}
                className="mono"
                style={{
                  minHeight: 38,
                  border: '1px solid var(--color-rule)',
                  borderRadius: 'var(--radius-full)',
                  background: interval === m ? 'var(--color-accent-bg)' : 'transparent',
                  color: interval === m ? 'var(--color-accent)' : 'var(--color-ink-3)',
                  padding: '0 var(--space-md)',
                  whiteSpace: 'nowrap',
                }}
              >
                {m}m
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="panel reveal" style={{ padding: 'var(--space-lg)' }}>
        <div className="flex items-center justify-between gap-md flex-wrap">
          <div>
            <p className="kicker">comment organism</p>
            <h2 style={{ color: 'var(--color-ink)', fontSize: 'var(--text-xl)', fontWeight: 800, letterSpacing: '-0.04em', marginTop: 'var(--space-xs)' }}>
              Azure DevOps auto-comment
            </h2>
            <p style={{ maxWidth: '68ch', color: 'var(--color-ink-3)', marginTop: 'var(--space-sm)', lineHeight: 1.65 }}>
              When enabled, completed reviews can post summary and inline comments with backend dedup protection.
            </p>
          </div>
          <Toggle enabled={autoComment} onChange={toggleAutoComment} loading={autoCommentLoading} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-sm" style={{ marginTop: 'var(--space-lg)' }}>
          <InfoTile label="summary" value={autoComment ? 'armed' : 'off'} Icon={MessageSquare} />
          <InfoTile label="inline" value={autoComment ? 'deduped' : 'off'} Icon={ShieldCheck} />
          <InfoTile label="mode" value="reviewed lines" Icon={RefreshCw} />
        </div>
      </section>

      {message && (
        <div
          className="panel"
          style={{
            position: 'fixed',
            right: 'var(--space-lg)',
            bottom: 'var(--space-lg)',
            zIndex: 'var(--z-toast)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-sm)',
            padding: 'var(--space-md)',
            borderColor: message.type === 'success' ? 'var(--color-rule-living)' : 'var(--color-danger)',
            color: message.type === 'success' ? 'var(--color-accent)' : 'var(--color-danger)',
          }}
        >
          {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {message.text}
        </div>
      )}
    </div>
  )
}

function InfoTile({ label, value, Icon }) {
  const Glyph = Icon
  return (
    <div className="panel-soft" style={{ padding: 'var(--space-md)' }}>
      <div className="flex items-center justify-between gap-sm">
        <p className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>{label}</p>
        {Glyph && <Glyph className="w-4 h-4" style={{ color: 'var(--color-accent)' }} />}
      </div>
      <p className="mono" style={{ color: 'var(--color-ink)', fontSize: 'var(--text-lg)', fontWeight: 800, marginTop: 'var(--space-sm)' }}>{value}</p>
    </div>
  )
}

const primaryButton = {
  minHeight: 48,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 'var(--space-xs)',
  border: 0,
  borderRadius: 'var(--radius-input)',
  padding: '0 var(--space-lg)',
  fontWeight: 800,
  whiteSpace: 'nowrap',
}

const secondaryButton = {
  ...primaryButton,
  border: '1px solid var(--color-rule-living)',
  background: 'var(--color-accent-bg)',
  color: 'var(--color-accent)',
}

export default SettingsPage
