import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type CalendarDay } from '../api/client'

export default function CalendarPage() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [data, setData] = useState<CalendarDay[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  useEffect(() => {
    setLoading(true)
    api.getCalendar(year, month + 1)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [year, month])

  function changeMonth(delta: number) {
    const d = new Date(year, month + delta, 1)
    setCurrentDate(d)
  }

  const calMap = new Map(data.map(d => [d.date, d]))
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const calendarDays = []
  for (let i = 0; i < firstDay; i++) calendarDays.push(null)
  for (let d = 1; d <= daysInMonth; d++) calendarDays.push(d)

  // Ensure 6 rows (42 cells) for consistent grid
  while (calendarDays.length < 42) calendarDays.push(null)

  const monthName = currentDate.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
  const todayStr = new Date().toISOString().split('T')[0]

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Calendar</h1>
          <p className="page-subtitle">Overview of scheduled appointments</p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-md)' }}>
          <button className="btn btn-secondary" onClick={() => setCurrentDate(new Date())}>Today</button>
          <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
            <button className="btn btn-secondary" onClick={() => changeMonth(-1)}>←</button>
            <span style={{ display: 'inline-flex', alignItems: 'center', fontWeight: 600, minWidth: 140, justifyContent: 'center' }}>{monthName}</span>
            <button className="btn btn-secondary" onClick={() => changeMonth(1)}>→</button>
          </div>
        </div>
      </div>

      <div className="card">
        {loading ? <div className="loading"><div className="spinner" />Loading calendar...</div> : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '1px', background: 'var(--border-secondary)' }}>
            {['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'].map(d => (
              <div key={d} style={{ padding: 'var(--space-md)', textAlign: 'center', fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--text-muted)', background: 'var(--bg-card)' }}>{d}</div>
            ))}

            {calendarDays.map((day, i) => {
              if (day === null) {
                return <div key={`empty-${i}`} style={{ background: 'var(--bg-card)', minHeight: 120, opacity: 0.5 }} />
              }

              const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
              const dayData = calMap.get(dateStr)
              const isToday = dateStr === todayStr

              return (
                <div
                  key={day}
                  style={{
                    background: isToday ? 'var(--bg-hover)' : 'var(--bg-card)',
                    minHeight: 120,
                    padding: 'var(--space-sm)',
                    cursor: 'pointer',
                    transition: 'background var(--transition-fast)'
                  }}
                  onClick={() => navigate(`/appointments?date_from=${dateStr}&date_to=${dateStr}`)}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-active)')}
                  onMouseLeave={e => (e.currentTarget.style.background = isToday ? 'var(--bg-hover)' : 'var(--bg-card)')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 28, height: 28,
                      borderRadius: '50%',
                      background: isToday ? 'var(--accent-primary)' : 'transparent',
                      color: isToday ? 'white' : 'var(--text-primary)',
                      fontWeight: isToday ? 600 : 400
                    }}>
                      {day}
                    </span>
                    {dayData && <span style={{ fontSize: 'var(--font-size-xs)', fontWeight: 600, color: 'var(--text-muted)' }}>{dayData.total}</span>}
                  </div>

                  {dayData && (
                    <div style={{ marginTop: 'var(--space-sm)', display: 'flex', flexDirection: 'column', gap: 2 }}>
                      {Object.entries(dayData.statuses).map(([s, count]) => (
                        <div key={s} className={`badge ${s}`} style={{ width: '100%', justifyContent: 'space-between', padding: '2px 6px' }}>
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{s}</span>
                          <span>{count}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
