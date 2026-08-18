import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type DashboardStats, type Call, type CalendarDay } from '../api/client'

function formatTime(date: Date) {
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(date: Date) {
  return date.toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

function getGreeting() {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

function relativeTime(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000)
  if (diff < 60) return 'Just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recentCalls, setRecentCalls] = useState<Call[]>([])
  const [calendarData, setCalendarData] = useState<CalendarDay[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const now = new Date()

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  async function loadData() {
    try {
      const [s, c, cal] = await Promise.all([
        api.getStats(),
        api.getCalls({ page: 1 }),
        api.getCalendar(now.getFullYear(), now.getMonth() + 1),
      ])
      setStats(s)
      setRecentCalls(c.data.slice(0, 8))
      setCalendarData(cal)
    } catch (e) {
      console.error('Failed to load dashboard:', e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="loading"><div className="spinner" />Loading dashboard...</div>
  }

  const kpis = [
    { label: 'Appointments Today', value: stats?.appointments_today ?? 0, meta: Object.entries(stats?.appointments_today_breakdown ?? {}).map(([k, v]) => `${v} ${k}`).join(' · ') || 'None', onClick: () => navigate('/appointments') },
    { label: 'Upcoming', value: stats?.upcoming_appointments ?? 0, meta: 'Future appointments', onClick: () => navigate('/appointments') },
    { label: 'Active Calls', value: stats?.active_calls ?? 0, meta: 'In progress now', onClick: () => navigate('/calls?status=in_progress') },
    { label: 'Completed Today', value: stats?.completed_calls_today ?? 0, meta: `${stats?.total_calls_today ?? 0} total today`, onClick: () => navigate('/calls') },
    { label: 'Booking Conversion', value: `${stats?.booking_conversion ?? 0}%`, meta: `${stats?.bookings_today ?? 0} bookings today`, onClick: () => navigate('/analytics') },
    { label: 'Emails', value: stats?.emails?.sent ?? 0, meta: `${stats?.emails?.pending ?? 0} pending · ${stats?.emails?.failed ?? 0} failed`, onClick: () => navigate('/emails') },
  ]

  // Calendar
  const year = now.getFullYear()
  const month = now.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const calMap = new Map(calendarData.map(d => [d.date, d]))

  const calendarDays = []
  for (let i = 0; i < firstDay; i++) calendarDays.push(null)
  for (let d = 1; d <= daysInMonth; d++) calendarDays.push(d)

  return (
    <div>
      <div className="greeting">
        <div className="greeting-text">{getGreeting()}, RUSBORN</div>
        <div className="greeting-time">{formatDate(now)} · {formatTime(now)}</div>
      </div>

      <div className="card-grid">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="kpi-card" onClick={kpi.onClick}>
            <div className="kpi-label">{kpi.label}</div>
            <div className="kpi-value">{kpi.value}</div>
            {kpi.meta && <div className="kpi-meta">{kpi.meta}</div>}
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 'var(--space-md)', alignItems: 'start' }}>
        {/* Recent Calls */}
        <div className="table-container">
          <div className="table-header">
            <span className="table-title">Recent Calls</span>
            <button className="btn btn-secondary" onClick={() => navigate('/calls')}>View all</button>
          </div>
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Status</th>
                <th>Outcome</th>
                <th>Duration</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {recentCalls.map((call) => (
                <tr key={call.id} onClick={() => navigate(`/calls/${call.id}`)}>
                  <td>
                    <div>{call.customers?.name ?? 'Unknown'}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>{call.customers?.company ?? ''}</div>
                  </td>
                  <td><span className={`badge ${call.status}`}>{call.status}</span></td>
                  <td><span className={`badge ${call.outcome ?? ''}`}>{call.outcome ?? '—'}</span></td>
                  <td>{call.duration_seconds ? `${Math.floor(call.duration_seconds / 60)}m ${call.duration_seconds % 60}s` : '—'}</td>
                  <td style={{ color: 'var(--text-secondary)' }}>{relativeTime(call.started_at)}</td>
                </tr>
              ))}
              {recentCalls.length === 0 && (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 'var(--space-xl)' }}>No calls yet</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Calendar */}
        <div className="calendar">
          <div className="calendar-header">
            <span className="calendar-title">{now.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</span>
            <button className="btn btn-secondary" onClick={() => navigate('/calendar')}>Full view</button>
          </div>
          <div className="calendar-grid">
            {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(d => (
              <div key={d} className="calendar-day-header">{d}</div>
            ))}
            {calendarDays.map((day, i) => {
              if (day === null) return <div key={`empty-${i}`} />
              const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
              const hasAppts = calMap.has(dateStr)
              const isToday = day === now.getDate()
              return (
                <div
                  key={day}
                  className={`calendar-day ${isToday ? 'today' : ''} ${hasAppts ? 'has-appointments' : ''}`}
                  onClick={() => navigate(`/appointments?date_from=${dateStr}&date_to=${dateStr}`)}
                >
                  {day}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Call Outcomes */}
      {stats?.call_outcomes && Object.keys(stats.call_outcomes).length > 0 && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <div className="detail-section-title">Call Outcomes (All Time)</div>
          <div style={{ display: 'flex', gap: 'var(--space-lg)', flexWrap: 'wrap' }}>
            {Object.entries(stats.call_outcomes).map(([outcome, count]) => (
              <div key={outcome} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 'var(--font-size-xl)', fontWeight: 700 }}>{count}</div>
                <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)' }}>{outcome.replace(/_/g, ' ')}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
