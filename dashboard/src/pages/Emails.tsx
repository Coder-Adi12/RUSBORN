import { useEffect, useState } from 'react'
import { api, type EmailDelivery, type PaginatedResponse } from '../api/client'

export default function Emails() {
  const [data, setData] = useState<PaginatedResponse<EmailDelivery> | null>(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [emailType, setEmailType] = useState('')
  const [page, setPage] = useState(1)

  useEffect(() => { loadData() }, [status, emailType, page])

  async function loadData() {
    setLoading(true)
    try { setData(await api.getEmails({ status: status || undefined, email_type: emailType || undefined, page })) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Email Deliveries</h1>
        <p className="page-subtitle">{data?.total ?? 0} total emails tracked</p>
      </div>

      <div className="filter-bar">
        <select className="select" value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}>
          <option value="">All Statuses</option>
          <option value="sent">Sent</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
        </select>
        <select className="select" value={emailType} onChange={e => { setEmailType(e.target.value); setPage(1) }}>
          <option value="">All Types</option>
          <option value="booking_confirmation">Booking Confirmation</option>
          <option value="reschedule_confirmation">Reschedule Confirmation</option>
          <option value="cancellation_confirmation">Cancellation Confirmation</option>
          <option value="sales_summary">Sales Summary</option>
        </select>
      </div>

      {loading ? <div className="loading"><div className="spinner" />Loading...</div> : (
        <div className="table-container">
          <table>
            <thead><tr><th>Recipient</th><th>Type</th><th>Subject</th><th>Status</th><th>Sent At</th></tr></thead>
            <tbody>
              {data?.data.map(e => (
                <tr key={e.id}>
                  <td>
                    <div style={{ fontWeight: 500 }}>{e.recipient_email}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>{e.customers?.name ?? 'Unknown'}</div>
                  </td>
                  <td>{e.email_type.replace(/_/g, ' ')}</td>
                  <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.subject ?? '—'}</td>
                  <td>
                    <span className={`badge ${e.status}`}>{e.status}</span>
                    {e.last_error && <div style={{ fontSize: '10px', color: 'var(--accent-red)', marginTop: 4 }}>{e.last_error}</div>}
                  </td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)' }}>
                    {e.sent_at ? new Date(e.sent_at).toLocaleString('en-IN') : '—'}
                  </td>
                </tr>
              ))}
              {data?.data.length === 0 && <tr><td colSpan={5}><div className="empty-state"><div className="empty-state-text">No emails found</div></div></td></tr>}
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
