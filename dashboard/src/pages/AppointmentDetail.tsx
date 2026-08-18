import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, type Appointment } from '../api/client'

export default function AppointmentDetail() {
  const { id } = useParams<{ id: string }>()
  const [appt, setAppt] = useState<Appointment | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => { if (id) api.getAppointment(id).then(setAppt).catch(console.error).finally(() => setLoading(false)) }, [id])

  if (loading) return <div className="loading"><div className="spinner" />Loading...</div>
  if (!appt) return <div className="empty-state"><div className="empty-state-text">Appointment not found</div></div>

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <button className="btn btn-secondary" onClick={() => navigate('/appointments')}>← Back</button>
          <div>
            <h1 className="page-title">{appt.customers?.name ?? 'Unknown'} — {appt.appointment_date}</h1>
            <p className="page-subtitle"><span className={`badge ${appt.status}`}>{appt.status}</span></p>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
        <div className="card">
          <div className="detail-section-title">Appointment</div>
          <div className="detail-row"><span className="detail-label">Date</span><span className="detail-value">{appt.appointment_date}</span></div>
          <div className="detail-row"><span className="detail-label">Time</span><span className="detail-value">{appt.start_time} – {appt.end_time}</span></div>
          <div className="detail-row"><span className="detail-label">Timezone</span><span className="detail-value">{appt.timezone}</span></div>
          <div className="detail-row"><span className="detail-label">Status</span><span className="detail-value"><span className={`badge ${appt.status}`}>{appt.status}</span></span></div>
          {appt.meeting_details && <div className="detail-row"><span className="detail-label">Details</span><span className="detail-value">{appt.meeting_details}</span></div>}
          {appt.cancellation_reason && <div className="detail-row"><span className="detail-label">Cancel Reason</span><span className="detail-value">{appt.cancellation_reason}</span></div>}
          {appt.reschedule_reason && <div className="detail-row"><span className="detail-label">Reschedule Reason</span><span className="detail-value">{appt.reschedule_reason}</span></div>}
        </div>

        <div className="card">
          <div className="detail-section-title">Customer</div>
          {appt.customers ? (
            <>
              <div className="detail-row"><span className="detail-label">Name</span><span className="detail-value">{appt.customers.name}</span></div>
              <div className="detail-row"><span className="detail-label">Email</span><span className="detail-value">{appt.customers.email ?? '—'}</span></div>
              <div className="detail-row"><span className="detail-label">Phone</span><span className="detail-value">{appt.customers.phone ?? '—'}</span></div>
              <div className="detail-row"><span className="detail-label">Company</span><span className="detail-value">{appt.customers.company ?? '—'}</span></div>
              <button className="btn btn-secondary" style={{ marginTop: 'var(--space-md)' }} onClick={() => navigate(`/customers/${appt.customers!.id}`)}>View Profile</button>
            </>
          ) : <div style={{ color: 'var(--text-muted)' }}>No customer linked</div>}
        </div>
      </div>

      {appt.call && (
        <div className="card" style={{ marginTop: 'var(--space-md)' }}>
          <div className="detail-section-title">Related Call</div>
          <div className="detail-row"><span className="detail-label">Status</span><span className="detail-value"><span className={`badge ${appt.call.status}`}>{appt.call.status}</span></span></div>
          <div className="detail-row"><span className="detail-label">Outcome</span><span className="detail-value">{appt.call.outcome ?? '—'}</span></div>
          {appt.call.summary && <div className="detail-row"><span className="detail-label">Summary</span><span className="detail-value">{appt.call.summary}</span></div>}
          <button className="btn btn-secondary" style={{ marginTop: 'var(--space-md)' }} onClick={() => navigate(`/calls/${appt.call!.id}`)}>View Call</button>
        </div>
      )}
    </div>
  )
}
