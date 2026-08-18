import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Customer, type PaginatedResponse } from '../api/client'

export default function Customers() {
  const [data, setData] = useState<PaginatedResponse<Customer> | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const navigate = useNavigate()

  useEffect(() => { loadData() }, [search, page])

  async function loadData() {
    setLoading(true)
    try { setData(await api.getCustomers({ search: search || undefined, page })) } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Customers</h1>
        <p className="page-subtitle">{data?.total ?? 0} customers</p>
      </div>
      <div className="filter-bar">
        <input className="input" style={{ maxWidth: 300 }} placeholder="Search by name, email, company..." value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} />
      </div>

      {loading ? <div className="loading"><div className="spinner" />Loading...</div> : (
        <div className="table-container">
          <table>
            <thead><tr><th>Name</th><th>Company</th><th>Email</th><th>Phone</th><th>Calls</th><th>Appointments</th><th>Last Active</th></tr></thead>
            <tbody>
              {data?.data.map(c => (
                <tr key={c.id} onClick={() => navigate(`/customers/${c.id}`)}>
                  <td style={{ fontWeight: 500 }}>{c.name}</td>
                  <td>{c.company ?? '—'}</td>
                  <td>{c.email ?? '—'}</td>
                  <td>{c.phone ?? '—'}</td>
                  <td>{c.total_calls ?? 0}</td>
                  <td>{c.total_appointments ?? 0}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)' }}>
                    {c.last_interaction ? new Date(c.last_interaction).toLocaleDateString('en-IN') : '—'}
                  </td>
                </tr>
              ))}
              {data?.data.length === 0 && <tr><td colSpan={7}><div className="empty-state"><div className="empty-state-text">No customers found</div></div></td></tr>}
            </tbody>
          </table>
          {totalPages > 1 && (
            <div className="pagination">
              <span className="pagination-info">Page {page} of {totalPages}</span>
              <div className="pagination-controls">
                <button className="btn btn-secondary" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
                <button className="btn btn-secondary" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
