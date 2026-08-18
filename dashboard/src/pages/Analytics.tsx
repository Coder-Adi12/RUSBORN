import { useEffect, useState } from 'react'
import { api, type AnalyticsData } from '../api/client'

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

  useEffect(() => {
    setLoading(true)
    api.getAnalytics(days)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days])

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Performance overview</p>
        </div>
        <select className="select" value={days} onChange={e => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 Days</option>
          <option value={30}>Last 30 Days</option>
          <option value={90}>Last 90 Days</option>
        </select>
      </div>

      {loading ? <div className="loading"><div className="spinner" />Loading analytics...</div> : !data ? <div className="empty-state">No data</div> : (
        <>
          <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 8 }}>Total Calls</div>
              <div style={{ fontSize: '32px', fontWeight: 700 }}>{data.total_calls}</div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 8 }}>Total Appointments</div>
              <div style={{ fontSize: '32px', fontWeight: 700 }}>{data.total_appointments}</div>
            </div>
            <div className="card" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 8 }}>Avg Call Duration</div>
              <div style={{ fontSize: '32px', fontWeight: 700 }}>{Math.floor(data.avg_call_duration / 60)}m {data.avg_call_duration % 60}s</div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
            <div className="card">
              <h3 style={{ marginBottom: 'var(--space-md)', fontSize: 'var(--font-size-md)' }}>Call Volume Trend</h3>
              <div style={{ display: 'flex', alignItems: 'flex-end', height: 200, gap: 4 }}>
                {data.calls_by_day.map((d, i) => {
                  const max = Math.max(...data.calls_by_day.map(x => x.total), 1)
                  const height = `${(d.total / max) * 100}%`
                  return (
                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 2, position: 'relative' }} title={`${d.date}: ${d.total} calls`}>
                      <div style={{ background: 'var(--accent-primary)', height, width: '100%', borderRadius: '2px 2px 0 0', opacity: 0.8 }} />
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="card">
              <h3 style={{ marginBottom: 'var(--space-md)', fontSize: 'var(--font-size-md)' }}>Appointment Booking Trend</h3>
              <div style={{ display: 'flex', alignItems: 'flex-end', height: 200, gap: 4 }}>
                {data.appointments_by_day.map((d, i) => {
                  const max = Math.max(...data.appointments_by_day.map(x => x.total), 1)
                  const height = `${(d.total / max) * 100}%`
                  return (
                    <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 2, position: 'relative' }} title={`${d.date}: ${d.total} appointments`}>
                      <div style={{ background: 'var(--accent-green)', height, width: '100%', borderRadius: '2px 2px 0 0', opacity: 0.8 }} />
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
