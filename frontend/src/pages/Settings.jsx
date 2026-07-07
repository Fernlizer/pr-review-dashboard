import { useState, useEffect } from 'react'
import { Settings as SettingsIcon, Play, Pause, Clock, RefreshCw, CheckCircle, XCircle } from 'lucide-react'

function SettingsPage() {
  const [status, setStatus] = useState(null)
  const [interval, setInterval] = useState(10)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState('')
  const [message, setMessage] = useState(null)

  const fetchStatus = async () => {
    try {
      const resp = await fetch('/api/scheduler/status')
      const data = await resp.json()
      setStatus(data)
      setInterval(data.interval_minutes)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Refresh status every 5 seconds
    const timer = setInterval(fetchStatus, 5000)
    return () => clearInterval(timer)
  }, [])

  const toggleScheduler = async () => {
    if (!status) return
    setActionLoading(status.enabled ? 'disable' : 'enable')
    setMessage(null)

    try {
      const endpoint = status.enabled ? '/api/scheduler/disable' : '/api/scheduler/enable'
      const resp = await fetch(endpoint, { method: 'POST' })
      const data = await resp.json()

      if (data.status === 'enabled' || data.status === 'disabled' || data.status === 'already_enabled' || data.status === 'already_disabled') {
        setMessage({ type: 'success', text: data.message || `Poller ${data.status}` })
      } else {
        setMessage({ type: 'error', text: data.detail || 'Unknown error' })
      }

      // Re-fetch real status from scheduler
      await fetchStatus()
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to toggle poller' })
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
        setMessage({ type: 'success', text: `Interval updated to ${interval} minutes` })
      } else {
        setMessage({ type: 'error', text: data.detail || 'Failed to update' })
      }

      await fetchStatus()
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to update interval' })
    } finally {
      setActionLoading('')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-6 h-6 animate-spin text-dark-400" />
      </div>
    )
  }

  return (
    <div className="p-8 space-y-8 max-w-2xl">
      <div>
        <h2 className="text-2xl font-bold text-dark-50 flex items-center gap-3">
          <SettingsIcon className="w-6 h-6" />
          Settings
        </h2>
        <p className="text-dark-400 mt-1">จัดการระบบตรวจสอบอัตโนมัติ</p>
      </div>

      {/* Status Indicator */}
      <div className="bg-dark-900 border border-dark-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-dark-200 mb-4">สถานะระบบ</h3>

        <div className="flex items-center gap-4 mb-6">
          {/* Status badge */}
          <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium ${
            status?.enabled
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}>
            {status?.enabled ? (
              <>
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                </span>
                กำลังทำงาน
              </>
            ) : (
              <>
                <span className="h-2.5 w-2.5 rounded-full bg-red-500"></span>
                หยุดอยู่
              </>
            )}
          </div>

          {/* Scheduler running */}
          <span className="text-xs text-dark-500">
            Scheduler: {status?.scheduler_running ? 'running' : 'stopped'}
          </span>
        </div>

        {/* Details */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-dark-800 rounded-lg p-4">
            <p className="text-xs text-dark-400 mb-1">Poll Interval</p>
            <p className="text-xl font-bold text-dark-100">{status?.interval_minutes} นาที</p>
          </div>
          <div className="bg-dark-800 rounded-lg p-4">
            <p className="text-xs text-dark-400 mb-1">Next Run</p>
            <p className="text-sm font-medium text-dark-100">
              {status?.next_run
                ? new Date(status.next_run).toLocaleString('th-TH')
                : '— (paused)'}
            </p>
          </div>
        </div>

        {/* Toggle Button */}
        <button
          onClick={toggleScheduler}
          disabled={!!actionLoading}
          className={`w-full flex items-center justify-center gap-3 px-6 py-3 rounded-xl text-base font-semibold transition-all ${
            status?.enabled
              ? 'bg-red-600 hover:bg-red-500 text-white'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white'
          } disabled:opacity-50`}
        >
          {actionLoading === 'enable' || actionLoading === 'disable' ? (
            <RefreshCw className="w-5 h-5 animate-spin" />
          ) : status?.enabled ? (
            <Pause className="w-5 h-5" />
          ) : (
            <Play className="w-5 h-5" />
          )}
          {actionLoading === 'enable' || actionLoading === 'disable'
            ? 'กำลังทำงาน...'
            : status?.enabled
              ? 'หยุดตรวจสอบอัตโนมัติ'
              : 'เปิดตรวจสอบอัตโนมัติ'}
        </button>
      </div>

      {/* Interval Settings */}
      <div className="bg-dark-900 border border-dark-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-dark-200 mb-4">ตั้งค่าเวลา</h3>

        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="block text-sm text-dark-400 mb-2">
              ความถี่ในการตรวจสอบ (นาที)
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={1440}
                value={interval}
                onChange={e => setInterval(parseInt(e.target.value) || 1)}
                className="w-32 bg-dark-800 border border-dark-600 text-dark-100 text-lg font-mono rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              />
              <span className="text-dark-400 text-sm">นาที</span>
            </div>
            <p className="text-xs text-dark-500 mt-1">1 - 1,440 นาที (สูงสุด 24 ชั่วโมง)</p>
          </div>

          <button
            onClick={updateInterval}
            disabled={!!actionLoading || interval === status?.interval_minutes}
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            {actionLoading === 'interval' ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Clock className="w-4 h-4" />
            )}
            {actionLoading === 'interval' ? 'กำลังอัพเดท...' : 'อัพเดท'}
          </button>
        </div>

        {/* Quick presets */}
        <div className="flex gap-2 mt-4">
          {[5, 10, 15, 30, 60].map(m => (
            <button
              key={m}
              onClick={() => setInterval(m)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                interval === m
                  ? 'bg-emerald-600 text-white'
                  : 'bg-dark-800 text-dark-400 hover:text-dark-200 hover:bg-dark-700'
              }`}
            >
              {m} นาที
            </button>
          ))}
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm ${
          message.type === 'success'
            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
            : 'bg-red-500/10 border border-red-500/20 text-red-400'
        }`}>
          {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {message.text}
        </div>
      )}
    </div>
  )
}

export default SettingsPage
