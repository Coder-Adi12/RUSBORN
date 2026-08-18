import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type Customer } from '../api/client'

export default function CustomerProfile() {
  const { id } = useParams<{ id: string }>()
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => { if (id) api.getCustomer(id).then(setCustomer).catch(console.error).finally(() => setLoading(false)) }, [id])

  if (loading) return <div className="loading"><div className="spinner" />Loading...</div>
  if (!customer) return <div className="empty-state"><div className="empty-state-text">Customer not found</div></div>

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/customers')}>← Back</button>
          <div>
            <h1 className="page-title">{customer.name}</h1>
            <p className="page-subtitle">{customer.company ?? 'Individual'}</p>
          </div>
        </div>
      </div>

      <div className="card-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
        <div className="card">
          <div className="detail-section-title">Contact Info</div>
          <div className="detail-row"><span className="detail-label">Email</span><span className="detail-value">{customer.email ?? '—'}</span></div>
          <div className="detail-row"><span className="detail-label">Phone</span><span className="detail-value">{customer.phone ?? '—'}</span></div>
          <div className="detail-row"><span className="detail-label">Company</span><span className="detail-value">{customer.company ?? '—'}</span></div>
          {customer.description && <div className="detail-row"><span className="detail-label">Notes</span><span className="detail-value">{customer.description}</span></div>}
          <div className="detail-row"><span className="detail-label">Added</span><span className="detail-value">{new Date(customer.created_at).toLocaleDateString('en-IN')}</span></div>
        </div>

        <div className="card">
          <div className="detail-section-title">History Summary</div>
          <div className="detail-row"><span className="detail-label">Total Calls</span><span className="detail-value">{customer.calls?.length ?? 0}</span></div>
          <div className="detail-row"><span className="detail-label">Total Appointments</span><span className="detail-value">{customer.appointments?.length ?? 0}</span></div>
          <div className="detail-row"><span className="detail-label">Total Emails</span><span className="detail-value">{customer.emails?.length ?? 0}</span></div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)', marginTop: 'var(--space-lg)' }}>
        {/* Calls List */}
        <div>
          <h3 style={{ marginBottom: 'var(--space-md)', fontSize: 'var(--font-size-md)' }}>Call History</h3>
          <div className="table-container">
            <table>
              <thead><tr><th>Status</th><th>Outcome</th><th>Date</th></tr></thead>
              <tbody>
                {customer.calls?.map(c => (
                  <tr key={c.id} onClick={() => navigate(`/calls/${c.id}`)}>
                    <td><span className={`badge ${c.status}`}>{c.status}</span></td>
                    <td>{c.outcome ?? '—'}</td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: 'var(--font-size-xs)' }}>
                      {c.started_at ? new Date(c.started_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—'}
                    </td>
                  </tr>
                ))}
                {!customer.calls?.length && <tr><td colSpan={3} style={{ textAlign: 'center', padding: 'var(--space-lg)', color: 'var(--text-muted)' }}>No calls</td></tr>}
              </tbody>
            </table>
          </div>
        </div>

        {/* Appointments List */}
        <div>
          <h3 style={{ marginBottom: 'var(--space-md)', fontSize: 'var(--font-size-md)' }}>Appointments</h3>
          <div className="table-container">
            <table>
              <thead><tr><th>Status</th><th>Date & Time</th></tr></thead>
              <tbody>
                {customer.appointments?.map(a => (
                  <tr key={a.id} onClick={() => navigate(`/appointments/${a.id}`)}>
                    <td><span className={`badge ${a.status}`}>{a.status}</span></td>
                    <td>{a.appointment_date} {a.start_time}</td>
                  </tr>
                ))}
                {!customer.appointments?.length && <tr><td colSpan={2} style={{ textAlign: 'center', padding: 'var(--space-lg)', color: 'var(--text-muted)' }}>No appointments</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
