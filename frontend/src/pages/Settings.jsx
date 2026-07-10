import { useState, useEffect } from 'react'
import {
  Settings as SettingsIcon, Play, Pause, Clock, RefreshCw,
  CheckCircle, XCircle, MessageSquare, Loader2, Info
} from 'lucide-react'

function LoadingSkeleton() {
  return (
    <div className="p-8 space-y-6 animate-fade-in max-w-2xl">
      <div className="space-y-2">
        <div className="skeleton h-7 w-48" />
        <div className="skeleton h-4 w-64" />
      </div>
      <div className="bg-surface border border-surface-border rounded-xl p-6">
        <div className="skeleton h-48 w-full" />
      </div>
      <div className="bg-surface border border-surface-border rounded-xl p-6">
        <div className="skeleton h-32 w-full" />
      </div>
    </div>
  )
}

function Toggle({ enabled, onChange, loading }) {
  return (
    <button
      onClick={onChange}
      disabled={loading}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:ring-offset-2 focus:ring-offset-dark-900 disabled:opacity-50 ${
        enabled ? 'bg-emerald-600' : 'bg-dark-600'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform duration-200 ${
          enabled ? 'translate-x-6' : 'translate-x-1'
        }`}
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

  return (
    <div className="p-8 space-y-6 max-w-2xl animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-dark-50 tracking-tight">Settings</h2>
        <p className="text-[13px] text-dark-400 mt-1">Manage the automated review system</p>
      </div>

      {/* Status Card */}
      <div className="bg-surface border border-surface-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border">
          <h3 className="text-[13px] font-semibold text-dark-300 uppercase tracking-wider">System Status</h3>
        </div>
        <div className="p-5 space-y-5">
          {/* Status indicator */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className={`relative flex h-2.5 w-2.5`}>
                {status?.enabled && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                )}
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  status?.enabled ? 'bg-emerald-500' : 'bg-dark-500'
                }`} />
              </span>
              <span className="text-[14px] font-medium text-dark-200">
                {status?.enabled ? 'Running' : 'Stopped'}
              </span>
            </div>
            <span className="text-[11px] text-dark-500 font-mono">
              Scheduler: {status?.scheduler_running ? 'active' : 'inactive'}
            </span>
          </div>

          {/* Info grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-dark-800/50 border border-surface-border rounded-lg p-4">
              <p className="text-[11px] text-dark-500 uppercase tracking-wide mb-1.5">Poll Interval</p>
              <p className="text-xl font-bold text-dark-100">
                {status?.interval_minutes} <span className="text-sm font-normal text-dark-400">min</span>
              </p>
            </div>
            <div className="bg-dark-800/50 border border-surface-border rounded-lg p-4">
              <p className="text-[11px] text-dark-500 uppercase tracking-wide mb-1.5">Next Run</p>
              <p className="text-sm font-medium text-dark-200">
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
            className={`w-full flex items-center justify-center gap-2.5 px-5 py-3 rounded-xl text-[14px] font-semibold transition-all duration-200 active:scale-[0.99] ${
              status?.enabled
                ? 'bg-red-600/90 hover:bg-red-600 text-white'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {actionLoading === 'enable' || actionLoading === 'disable' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
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
      <div className="bg-surface border border-surface-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border">
          <h3 className="text-[13px] font-semibold text-dark-300 uppercase tracking-wider">Poll Interval</h3>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-[13px] text-dark-400 mb-2">
              Frequency (minutes)
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={1440}
                value={interval}
                onChange={e => setIntervalState(parseInt(e.target.value) || 1)}
                className="w-28 bg-dark-800/50 border border-surface-border text-dark-100 text-lg font-mono rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all"
              />
              <span className="text-[13px] text-dark-500">minutes</span>
            </div>
            <p className="text-[11px] text-dark-600 mt-1.5">1 – 1,440 minutes (max 24 hours)</p>
          </div>

          {/* Presets */}
          <div className="flex gap-2">
            {[5, 10, 15, 30, 60].map(m => (
              <button
                key={m}
                onClick={() => setIntervalState(m)}
                className={`px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-150 ${
                  interval === m
                    ? 'bg-emerald-600 text-white'
                    : 'bg-dark-800 text-dark-400 hover:text-dark-200 hover:bg-dark-700 border border-surface-border'
                }`}
              >
                {m}m
              </button>
            ))}
          </div>

          <button
            onClick={updateInterval}
            disabled={!!actionLoading || interval === status?.interval_minutes}
            className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-[13px] font-medium transition-all duration-150 active:scale-[0.98]"
          >
            {actionLoading === 'interval' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
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
      <div className="bg-surface border border-surface-border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border">
          <h3 className="text-[13px] font-semibold text-dark-300 uppercase tracking-wider">Auto-Comment</h3>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[14px] text-dark-200 font-medium">Post comments on Azure DevOps</p>
              <p className="text-[12px] text-dark-500 mt-0.5">
                Automatically comment review results on PRs after completion
              </p>
            </div>
            <Toggle enabled={autoComment} onChange={toggleAutoComment} loading={autoCommentLoading} />
          </div>

          {autoComment && (
            <div className="bg-dark-800/50 border border-surface-border rounded-lg p-4 animate-slide-down">
              <div className="flex items-center gap-2 mb-3">
                <Info className="w-4 h-4 text-blue-400" />
                <p className="text-[13px] font-medium text-dark-200">When a review completes, the system will:</p>
              </div>
              <ul className="space-y-2 text-[13px] text-dark-300">
                <li className="flex items-start gap-2">
                  <MessageSquare className="w-3.5 h-3.5 text-dark-500 mt-0.5 flex-shrink-0" />
                  <span>Post a <strong className="text-dark-100">summary comment</strong> on the PR thread (scores + recommendation)</span>
                </li>
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400 mt-0.5 flex-shrink-0" />
                  <span>Post <strong className="text-dark-100">inline comments</strong> on lines with HIGH/MEDIUM findings</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400 mt-0.5 flex-shrink-0" />
                  <span>Include <strong className="text-dark-100">fix suggestions</strong> in every comment</span>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Toast message */}
      {message && (
        <div
          className={`fixed bottom-6 right-6 flex items-center gap-3 px-4 py-3 rounded-xl text-[13px] shadow-lg border animate-slide-up ${
            message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-red-500/10 border-red-500/20 text-red-400'
          }`}
        >
          {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {message.text}
        </div>
      )}
    </div>
  )
}

export default SettingsPage
