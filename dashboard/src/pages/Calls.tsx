import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, type Call, type PaginatedResponse } from '../api/client'

export default function Calls() {
  const [data, setData] = useState<PaginatedResponse<Call> | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const status = searchParams.get('status') || ''
  const search = searchParams.get('search') || ''
  const page = Number(searchParams.get('page') || '1')

  useEffect(() => { loadData() }, [status, search, page])

  async function loadData() {
    setLoading(true)
    try {
      const result = await api.getCalls({ status: status || undefined, search: search || undefined, page })
      setData(result)
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  function setFilter(key: string, value: string) {
    const sp = new URLSearchParams(searchParams)
    if (value) sp.set(key, value)
    else sp.delete(key)
    sp.set('page', '1')
    setSearchParams(sp)
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Calls</h1>
        <p className="page-subtitle">{data?.total ?? 0} total calls</p>
      </div>

      <div className="filter-bar">
        {['all', 'in_progress', 'completed', 'failed'].map(s => (
          <button key={s} className={`btn ${(status || 'all') === s ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setFilter('status', s === 'all' ? '' : s)}>
            {s === 'all' ? 'All' : s.replace(/_/g, ' ')}
          </button>
        ))}
        <input className="input" style={{ maxWidth: 240 }} placeholder="Search calls..." value={search} onChange={e => setFilter('search', e.target.value)} />
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" />Loading...</div>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr><th>Customer</th><th>Direction</th><th>Status</th><th>Outcome</th><th>Duration</th><th>Started</th></tr>
            </thead>
            <tbody>
              {data?.data.map(call => (
                <tr key={call.id} onClick={() => navigate(`/calls/${call.id}`)}>
                  <td>
                    <div>{call.customers?.name ?? 'Unknown'}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>{call.customers?.company ?? ''}</div>
                  </td>
                  <td>{call.direction}</td>
                  <td><span className={`badge ${call.status}`}>{call.status}</span></td>
                  <td><span className={`badge ${call.outcome ?? ''}`}>{call.outcome ?? '—'}</span></td>
                  <td>{call.duration_seconds ? `${Math.floor(call.duration_seconds / 60)}m ${call.duration_seconds % 60}s` : '—'}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)' }}>
                    {call.started_at ? new Date(call.started_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'}
                  </td>
                </tr>
              ))}
              {data?.data.length === 0 && (
                <tr><td colSpan={6}><div className="empty-state"><div className="empty-state-text">No calls found</div></div></td></tr>
              )}
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
