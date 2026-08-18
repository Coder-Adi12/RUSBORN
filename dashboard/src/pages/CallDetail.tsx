import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type Call } from '../api/client'

export default function CallDetail() {
  const { id } = useParams<{ id: string }>()
  const [call, setCall] = useState<Call | null>(null)
  const [loading, setLoading] = useState(true)
  const [showTechnical, setShowTechnical] = useState(false)
  const navigate = useNavigate()

  useEffect(() => { if (id) api.getCall(id).then(setCall).catch(console.error).finally(() => setLoading(false)) }, [id])

  if (loading) return <div className="loading"><div className="spinner" />Loading...</div>
  if (!call) return <div className="empty-state"><div className="empty-state-text">Call not found</div></div>

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/calls')}>← Back</button>
          <div>
            <h1 className="page-title">{call.customers?.name ?? 'Unknown Customer'}</h1>
            <p className="page-subtitle">{call.customers?.company ?? ''} · <span className={`badge ${call.status}`}>{call.status}</span></p>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
        <div className="card">
          <div className="detail-section-title">Call Metadata</div>
          <div className="detail-row"><span className="detail-label">Direction</span><span className="detail-value">{call.direction}</span></div>
          <div className="detail-row"><span className="detail-label">Started</span><span className="detail-value">{call.started_at ? new Date(call.started_at).toLocaleString('en-IN') : '—'}</span></div>
          <div className="detail-row"><span className="detail-label">Ended</span><span className="detail-value">{call.ended_at ? new Date(call.ended_at).toLocaleString('en-IN') : '—'}</span></div>
          <div className="detail-row"><span className="detail-label">Duration</span><span className="detail-value">{call.duration_seconds ? `${Math.floor(call.duration_seconds / 60)}m ${call.duration_seconds % 60}s` : '—'}</span></div>
          <div className="detail-row"><span className="detail-label">Outcome</span><span className="detail-value"><span className={`badge ${call.outcome ?? ''}`}>{call.outcome ?? '—'}</span></span></div>
        </div>

        <div className="card">
          <div className="detail-section-title">Customer</div>
          {call.customers ? (
            <>
              <div className="detail-row"><span className="detail-label">Name</span><span className="detail-value">{call.customers.name}</span></div>
              <div className="detail-row"><span className="detail-label">Email</span><span className="detail-value">{call.customers.email ?? '—'}</span></div>
              <div className="detail-row"><span className="detail-label">Phone</span><span className="detail-value">{call.customers.phone ?? '—'}</span></div>
              <div className="detail-row"><span className="detail-label">Company</span><span className="detail-value">{call.customers.company ?? '—'}</span></div>
              <button className="btn btn-secondary" style={{ marginTop: 'var(--space-md)' }} onClick={() => navigate(`/customers/${call.customers!.id}`)}>View Profile</button>
            </>
          ) : <div style={{ color: 'var(--text-muted)' }}>No customer linked</div>}
        </div>
      </div>

      {call.summary && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <div className="detail-section-title">AI Summary</div>
          <p style={{ lineHeight: 1.7, color: 'var(--text-secondary)' }}>{call.summary}</p>
        </div>
      )}

      {call.appointments && call.appointments.length > 0 && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <div className="detail-section-title">Related Appointments</div>
          {call.appointments.map(a => (
            <div key={a.id} className="detail-row" style={{ cursor: 'pointer' }} onClick={() => navigate(`/appointments/${a.id}`)}>
              <span className="detail-label">{a.appointment_date} {a.start_time}</span>
              <span className="detail-value"><span className={`badge ${a.status}`}>{a.status}</span> {a.meeting_details ?? ''}</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 'var(--space-md)' }}>
        <button className="btn btn-secondary" onClick={() => setShowTechnical(!showTechnical)}>
          {showTechnical ? '▾ Hide' : '▸ Show'} Technical Details
        </button>
        {showTechnical && (
          <div className="card" style={{ marginTop: 'var(--space-sm)' }}>
            <div className="detail-row"><span className="detail-label">Call ID</span><span className="detail-value" style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>{call.id}</span></div>
            <div className="detail-row"><span className="detail-label">Room</span><span className="detail-value" style={{ fontFamily: 'monospace' }}>{call.livekit_room_id}</span></div>
            <div className="detail-row"><span className="detail-label">Customer ID</span><span className="detail-value" style={{ fontFamily: 'monospace', fontSize: 'var(--font-size-xs)' }}>{call.customer_id ?? '—'}</span></div>
            <div className="detail-row"><span className="detail-label">Created</span><span className="detail-value">{new Date(call.created_at).toLocaleString('en-IN')}</span></div>
          </div>
        )}
      </div>
    </div>
  )
}
