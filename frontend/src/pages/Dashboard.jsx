/* Hallmark · genre: atmospheric · macrostructure: Workbench · design-system: design.md · designed-as-app */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  GitPullRequest, FileSearch, AlertTriangle, Flame,
  CheckCircle, XCircle, MessageSquare, ArrowUpRight
} from 'lucide-react'

/* ── Card base ───────────────────────────────────────────────────── */

const cardStyle = {
  background: 'var(--color-paper-2)',
  border: '1px solid var(--color-rule)',
  borderRadius: 'var(--radius-lg)',
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
    <div className="p-lg space-y-lg animate-fade-in">
      <div className="space-y-2xs">
        <div className="skeleton" style={{ height: 28, width: 180 }} />
        <div className="skeleton" style={{ height: 16, width: 260 }} />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-sm">
        {[...Array(4)].map((_, i) => (
          <div key={i} style={{ ...cardStyle, padding: 'var(--space-md)' }}>
            <div className="skeleton" style={{ height: 14, width: 72, marginBottom: 12 }} />
            <div className="skeleton" style={{ height: 32, width: 56 }} />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-sm">
        <div className="md:col-span-3" style={{ ...cardStyle, padding: 'var(--space-md)' }}>
          <div className="skeleton" style={{ height: 120 }} />
        </div>
        <div className="md:col-span-2" style={{ ...cardStyle, padding: 'var(--space-md)' }}>
          <div className="skeleton" style={{ height: 120 }} />
        </div>
      </div>
    </div>
  )
}

/* ── Stat Card ───────────────────────────────────────────────────── */

function StatCard({ label, value, icon: Icon, accentVar }) {
  return (
    <div
      className="group"
      style={{ ...cardStyle, padding: 'var(--space-md)', transition: `border-color var(--dur-micro) var(--ease-out)` }}
      onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-paper-4)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--color-rule)'}
    >
      <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-sm)' }}>
        <span className="font-medium" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)' }}>
          {label}
        </span>
        <div
          className="rounded-md flex items-center justify-center"
          style={{ width: 28, height: 28, background: 'var(--color-accent-bg)' }}
        >
          <Icon className="w-3.5 h-3.5" style={{ color: `var(${accentVar})` }} />
        </div>
      </div>
      <p
        className="font-bold tracking-tight font-mono"
        style={{
          fontSize: 'var(--text-2xl)',
          color: 'var(--color-ink)',
          lineHeight: 1,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {value}
      </p>
    </div>
  )
}

/* ── Recommendation card ─────────────────────────────────────────── */

function RecommendationCard({ label, value, icon: Icon, accentVar }) {
  return (
    <div style={{ ...cardStyle, padding: '10px var(--space-md)', display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
      <div
        className="rounded-md flex items-center justify-center flex-shrink-0"
        style={{ width: 32, height: 32, background: 'var(--color-accent-bg)' }}
      >
        <Icon className="w-4 h-4" style={{ color: `var(${accentVar})` }} />
      </div>
      <div>
        <p
          className="font-bold leading-none font-mono"
          style={{ fontSize: 'var(--text-lg)', color: 'var(--color-ink)', fontVariantNumeric: 'tabular-nums' }}
        >
          {value}
        </p>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-3)', marginTop: 2 }}>{label}</p>
      </div>
    </div>
  )
}

/* ── Severity bar ────────────────────────────────────────────────── */

function SeverityBar({ label, count, total, accentVar }) {
  const pct = total > 0 ? (count / total) * 100 : 0
  return (
    <div className="flex items-center gap-sm">
      <span className="flex-shrink-0 font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-3)', width: 56 }}>
        {label}
      </span>
      <div className="flex-1 overflow-hidden" style={{ height: 6, background: 'var(--color-paper-3)', borderRadius: 'var(--radius-full)' }}>
        <div
          style={{
            height: '100%',
            width: `${Math.max(pct, count > 0 ? 8 : 0)}%`,
            background: `var(${accentVar})`,
            borderRadius: 'var(--radius-full)',
            transition: 'width 0.7s var(--ease-out)',
          }}
        />
      </div>
      <span className="font-medium text-right font-mono" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)', width: 32 }}>
        {count}
      </span>
    </div>
  )
}

/* ── Empty state ─────────────────────────────────────────────────── */

function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center" style={{ padding: 'var(--space-3xl) var(--space-lg)' }}>
      <div
        className="rounded-lg flex items-center justify-center"
        style={{ width: 48, height: 48, background: 'var(--color-paper-3)', marginBottom: 'var(--space-md)' }}
      >
        <Icon className="w-5 h-5" style={{ color: 'var(--color-ink-4)' }} />
      </div>
      <p className="font-medium" style={{ fontSize: 'var(--text-base)', color: 'var(--color-ink-2)' }}>{title}</p>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)', marginTop: 4, textAlign: 'center', maxWidth: 320 }}>{description}</p>
    </div>
  )
}

/* ── Recommendation badge ────────────────────────────────────────── */

function RecommendationBadge({ rec }) {
  const config = {
    approve: { bg: 'var(--color-success-bg)', text: 'var(--color-success)', label: 'Approve' },
    request_changes: { bg: 'var(--color-danger-bg)', text: 'var(--color-danger)', label: 'Changes' },
    comment: { bg: 'var(--color-warning-bg)', text: 'var(--color-warning)', label: 'Comment' },
  }
  const c = config[rec] || { bg: 'var(--color-paper-3)', text: 'var(--color-ink-2)', label: rec }

  return (
    <span
      className="inline-flex items-center font-medium flex-shrink-0 font-mono"
      style={{ background: c.bg, color: c.text, padding: '3px 8px', borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-xs)' }}
    >
      {c.label}
    </span>
  )
}

/* ── Dashboard ───────────────────────────────────────────────────── */

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recentReviews, setRecentReviews] = useState([])

  useEffect(() => {
    fetch('/api/stats').then(r => r.json()).then(setStats)
    fetch('/api/reviews?limit=10').then(r => r.json()).then(d => setRecentReviews(d.reviews || []))
  }, [])

  if (!stats) return <LoadingSkeleton />

  const totalFindings = stats.total_findings || 0
  const highCount = stats.findings_by_severity?.HIGH || 0
  const medCount = stats.findings_by_severity?.MEDIUM || 0
  const lowCount = stats.findings_by_severity?.LOW || 0

  return (
    <div className="p-lg space-y-lg animate-fade-in" style={{ maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ '--i': 0 }} className="reveal">
        <h2 className="font-semibold tracking-tight" style={{ fontSize: 'var(--text-xl)', color: 'var(--color-ink)', letterSpacing: '-0.025em' }}>
          Dashboard
        </h2>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)', marginTop: 4 }}>
          Automated PR security review overview
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-sm reveal" style={{ '--i': 1 }}>
        <StatCard label="Total PRs" value={stats.total_prs} icon={GitPullRequest} accentVar="--color-info" />
        <StatCard label="Reviews" value={stats.total_reviews} icon={FileSearch} accentVar="--color-accent" />
        <StatCard label="Findings" value={totalFindings} icon={AlertTriangle} accentVar="--color-warning" />
        <StatCard label="Critical" value={highCount} icon={Flame} accentVar="--color-danger" />
      </div>

      {/* Recommendation + Severity row */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-sm reveal" style={{ '--i': 2 }}>
        <div className="md:col-span-3" style={{ ...cardStyle, padding: 'var(--space-md)' }}>
          <h3 style={sectionLabel}>Recommendations</h3>
          <div className="grid grid-cols-3 gap-xs" style={{ marginTop: 'var(--space-sm)' }}>
            <RecommendationCard label="Approved" value={stats.recommendations?.approve || 0} icon={CheckCircle} accentVar="--color-success" />
            <RecommendationCard label="Changes" value={stats.recommendations?.request_changes || 0} icon={XCircle} accentVar="--color-danger" />
            <RecommendationCard label="Comments" value={stats.recommendations?.comment || 0} icon={MessageSquare} accentVar="--color-warning" />
          </div>
        </div>

        <div className="md:col-span-2" style={{ ...cardStyle, padding: 'var(--space-md)' }}>
          <h3 style={sectionLabel}>Findings by Severity</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', marginTop: 'var(--space-md)' }}>
            <SeverityBar label="HIGH" count={highCount} total={totalFindings} accentVar="--color-danger" />
            <SeverityBar label="MEDIUM" count={medCount} total={totalFindings} accentVar="--color-warning" />
            <SeverityBar label="LOW" count={lowCount} total={totalFindings} accentVar="--color-info" />
          </div>
        </div>
      </div>

      {/* Poll Status */}
      {stats.poll_states?.length > 0 && (
        <div className="reveal" style={{ ...cardStyle, padding: 'var(--space-md)', '--i': 3 }}>
          <h3 style={sectionLabel}>Poll Status</h3>
          <div style={{ marginTop: 'var(--space-sm)' }}>
            {stats.poll_states.map(ps => (
              <div
                key={ps.repo}
                className="flex items-center justify-between"
                style={{ padding: 'var(--space-xs) 0', borderBottom: '1px solid var(--color-rule)' }}
              >
                <div className="flex items-center gap-2xs">
                  <div className="rounded-full" style={{ width: 6, height: 6, background: 'var(--color-accent)' }} />
                  <span className="font-mono" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>{ps.repo}</span>
                </div>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)' }}>
                  {ps.last_poll_at ? new Date(ps.last_poll_at).toLocaleString('th-TH') : 'Never'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Reviews */}
      <div className="reveal" style={{ ...cardStyle, overflow: 'hidden', '--i': 4 }}>
        <div className="px-md py-sm border-b" style={{ borderColor: 'var(--color-rule)' }}>
          <h3 style={sectionLabel}>Recent Reviews</h3>
        </div>
        {recentReviews.length === 0 ? (
          <EmptyState icon={FileSearch} title="No reviews yet" description="Reviews will appear here once PRs are scanned by the security scanner." />
        ) : (
          <div>
            {recentReviews.map((rv) => (
              <Link
                key={rv.id}
                to={`/prs/${rv.pr_id}`}
                className="flex items-center justify-between group"
                style={{
                  padding: 'var(--space-xs) var(--space-md)',
                  borderBottom: '1px solid var(--color-rule)',
                  textDecoration: 'none',
                  transition: `background var(--dur-micro) var(--ease-out)`,
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--color-paper-3)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <div className="flex items-center gap-sm min-w-0">
                  <RecommendationBadge rec={rv.recommendation} />
                  <div className="min-w-0">
                    <p className="font-medium truncate" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink)', maxWidth: 400 }}>
                      {rv.pr_title || `PR #${rv.pr_id}`}
                    </p>
                    <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)', marginTop: 2 }}>
                      {rv.pr_repo} · {rv.author}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-sm flex-shrink-0" style={{ marginLeft: 'var(--space-md)' }}>
                  <div className="flex items-center gap-2xs">
                    {rv.high_count > 0 && (
                      <span className="font-mono font-medium" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-danger)', background: 'var(--color-danger-bg)', padding: '2px 6px', borderRadius: 'var(--radius-sm)' }}>
                        {rv.high_count}H
                      </span>
                    )}
                    {rv.medium_count > 0 && (
                      <span className="font-mono font-medium" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-warning)', background: 'var(--color-warning-bg)', padding: '2px 6px', borderRadius: 'var(--radius-sm)' }}>
                        {rv.medium_count}M
                      </span>
                    )}
                    {rv.low_count > 0 && (
                      <span className="font-mono font-medium" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-info)', background: 'var(--color-info-bg)', padding: '2px 6px', borderRadius: 'var(--radius-sm)' }}>
                        {rv.low_count}L
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)' }}>{rv.duration_seconds}s</span>
                  <ArrowUpRight className="w-3.5 h-3.5" style={{ color: 'var(--color-ink-4)', transition: `color var(--dur-micro) var(--ease-out)` }} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
