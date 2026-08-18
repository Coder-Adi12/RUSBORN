import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, type Appointment, type PaginatedResponse } from '../api/client'

export default function Appointments() {
  const [data, setData] = useState<PaginatedResponse<Appointment> | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const status = searchParams.get('status') || ''
  const dateFrom = searchParams.get('date_from') || ''
  const dateTo = searchParams.get('date_to') || ''
  const search = searchParams.get('search') || ''
  const page = Number(searchParams.get('page') || '1')

  useEffect(() => { loadData() }, [status, dateFrom, dateTo, search, page])

  async function loadData() {
    setLoading(true)
    try {
      const result = await api.getAppointments({ status: status || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined, search: search || undefined, page })
      setData(result)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  function setFilter(key: string, value: string) {
    const sp = new URLSearchParams(searchParams)
    if (value) sp.set(key, value); else sp.delete(key)
    sp.set('page', '1')
    setSearchParams(sp)
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Appointments</h1>
        <p className="page-subtitle">{data?.total ?? 0} total appointments</p>
      </div>
      <div className="filter-bar">
        {['all', 'booked', 'confirmed', 'rescheduled', 'cancelled', 'completed'].map(s => (
          <button key={s} className={`btn ${(status || 'all') === s ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setFilter('status', s === 'all' ? '' : s)}>
            {s === 'all' ? 'All' : s}
          </button>
        ))}
        <input type="date" className="input" style={{ maxWidth: 160 }} value={dateFrom} onChange={e => setFilter('date_from', e.target.value)} />
        <input type="date" className="input" style={{ maxWidth: 160 }} value={dateTo} onChange={e => setFilter('date_to', e.target.value)} />
        <input className="input" style={{ maxWidth: 200 }} placeholder="Search..." value={search} onChange={e => setFilter('search', e.target.value)} />
      </div>

      {loading ? <div className="loading"><div className="spinner" />Loading...</div> : (
        <div className="table-container">
          <table>
            <thead><tr><th>Customer</th><th>Date</th><th>Time</th><th>Status</th><th>Details</th><th>Created</th></tr></thead>
            <tbody>
              {data?.data.map(a => (
                <tr key={a.id} onClick={() => navigate(`/appointments/${a.id}`)}>
                  <td>
                    <div>{a.customers?.name ?? 'Unknown'}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>{a.customers?.company ?? ''}</div>
                  </td>
                  <td>{a.appointment_date}</td>
                  <td>{a.start_time}–{a.end_time}</td>
                  <td><span className={`badge ${a.status}`}>{a.status}</span></td>
                  <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.meeting_details ?? '—'}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)' }}>{new Date(a.created_at).toLocaleDateString('en-IN')}</td>
                </tr>
              ))}
              {data?.data.length === 0 && <tr><td colSpan={6}><div className="empty-state"><div className="empty-state-text">No appointments found</div></div></td></tr>}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div className="pagination">
              <span className="pagination-info">Page {page} of {totalPages}</span>
              <div className="pagination-controls">
                <button className="btn btn-secondary" disabled={page <= 1} onClick={() => setFilter('page', String(page - 1))}>← Prev</button>
                <button className="btn btn-secondary" disabled={page >= totalPages} onClick={() => setFilter('page', String(page + 1))}>Next →</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
