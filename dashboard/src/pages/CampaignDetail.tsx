import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { campaignsApi, type Campaign, type CampaignActivity } from '../api/client'
import { 
  Play, Pause, Square, Users, Phone, Clock, 
  PhoneCall, CheckCircle, PhoneOff, AlertCircle, 
  ShieldOff, ChevronLeft
} from 'lucide-react'

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [progress, setProgress] = useState<Record<string, number>>({})
  const [activities, setActivities] = useState<CampaignActivity[]>([])
  const [audience, setAudience] = useState<any[]>([])
  const [validationResult, setValidationResult] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    if (!id) return
    try {
      const camp = await campaignsApi.getCampaign(id)
      setCampaign(camp)
      const prog = await campaignsApi.getProgress(id)
      setProgress(prog)
      const acts = await campaignsApi.getActivity(id)
      setActivities(acts)
      const aud = await campaignsApi.getAudience(id)
      setAudience(aud)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [id])

  if (loading && !campaign) return <div style={{ padding: 'var(--space-2xl)', textAlign: 'center', color: 'var(--text-muted)' }}>Loading campaign data...</div>
  if (!campaign) return <div style={{ padding: 'var(--space-2xl)', textAlign: 'center', color: 'var(--accent-red)' }}>Campaign not found.</div>

  const handleValidate = async () => {
    try {
      const res = await campaignsApi.validateCampaign(campaign.id)
      setValidationResult(res)
      fetchData()
    } catch (err: any) {
      alert(err.message || 'Validation failed')
    }
  }

  const handleStart = async () => {
    if (!confirm(`You are about to start outbound calls. Proceed?`)) return
    try {
      await campaignsApi.startCampaign(campaign.id)
      fetchData()
    } catch (err: any) {
      alert(err.message)
    }
  }

  const handlePause = async () => {
    try {
      await campaignsApi.pauseCampaign(campaign.id)
      fetchData()
    } catch (err: any) {
      alert(err.message)
    }
  }

  const handleStop = async () => {
    if (!confirm('Are you sure you want to stop this campaign?')) return
    try {
      await campaignsApi.stopCampaign(campaign.id)
      fetchData()
    } catch (err: any) {
      alert(err.message)
    }
  }
  
  const handleRemoveContact = async (contactId: string) => {
    if (!confirm('Remove this contact?')) return
    try {
      await campaignsApi.deleteAudienceMember(campaign.id, contactId)
      fetchData()
    } catch (err: any) {
      alert(err.message)
    }
  }

  // Calculate advanced analytics
  const total = progress.total || 0
  const callable = total - (progress.dnc || 0) - (progress.invalid_phone || 0) - (progress.duplicate || 0)
  const completedCount = progress.completed || 0
  const completionPercentage = total > 0 ? Math.round((completedCount / total) * 100) : 0

  const getStatusBadgeClass = (status: string) => {
    switch(status) {
      case 'DRAFT': return 'badge claim'
      case 'READY': return 'badge pending'
      case 'RUNNING': return 'badge in_progress'
      case 'PAUSED': return 'badge warning'
      case 'COMPLETED': return 'badge completed'
      case 'STOPPED': return 'badge'
      case 'FAILED': return 'badge error'
      case 'DNC': return 'badge internal'
      case 'NO_ANSWER': return 'badge warning'
      default: return 'badge'
    }
  }

  return (
    <div>
      <div className="campaign-header-row">
        <div className="header-title-row">
          <button className="btn btn-secondary" onClick={() => navigate('/campaigns')} style={{ padding: '8px', border: 'none' }}>
            <ChevronLeft size={20} />
          </button>
          <div className="header-title-group">
            <h1 className="page-title" style={{ margin: 0 }}>{campaign.name}</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
              <span className="page-subtitle" style={{ margin: 0 }}>{campaign.objective} · Max {campaign.max_concurrent_calls} calls</span>
              <span className={getStatusBadgeClass(campaign.status)} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {campaign.status === 'RUNNING' && <span className="status-dot healthy" />}
                {campaign.status}
              </span>
            </div>
          </div>
        </div>
        
        <div className="header-actions">
          {campaign.status === 'DRAFT' && (
            <button className="btn btn-secondary" onClick={handleValidate}>Validate Audience</button>
          )}
          {(campaign.status === 'READY' || campaign.status === 'PAUSED') && (
            <button className="btn btn-primary" onClick={handleStart}>
              <Play size={16} /> Start Campaign
            </button>
          )}
          {campaign.status === 'RUNNING' && (
            <button className="btn btn-secondary" onClick={handlePause}>
              <Pause size={16} /> Pause
            </button>
          )}
          {(campaign.status === 'RUNNING' || campaign.status === 'PAUSED') && (
            <button className="btn btn-secondary" onClick={handleStop} style={{ color: 'var(--accent-red)' }}>
              <Square size={16} /> Stop
            </button>
          )}
        </div>
      </div>

      <div style={{ marginBottom: 'var(--space-2xl)' }}>
        <div className="progress-header">
          <div style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>Campaign Progress</div>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>{completionPercentage}% ({completedCount} of {total} completed)</div>
        </div>
        <div className="progress-container">
          <div className="progress-bar-fill" style={{ width: `${completionPercentage}%` }}></div>
        </div>
      </div>

      {validationResult && validationResult.valid_contacts_count !== undefined && (
        <div style={{ padding: 'var(--space-md)', background: 'var(--accent-blue-bg)', color: 'var(--accent-blue)', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-lg)', display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <CheckCircle size={18} />
          Validation passed! <strong>{validationResult.valid_contacts_count}</strong> dialable contacts.
        </div>
      )}

      <div className="card-grid">
        <div className="kpi-card">
          <Users size={20} className="kpi-icon" />
          <div className="kpi-label">Total Contacts</div>
          <div className="kpi-value">{total}</div>
        </div>
        <div className="kpi-card">
          <Phone size={20} className="kpi-icon" />
          <div className="kpi-label">Callable</div>
          <div className="kpi-value" style={{ color: 'var(--accent-blue)' }}>{callable}</div>
        </div>
        <div className="kpi-card">
          <Clock size={20} className="kpi-icon" />
          <div className="kpi-label">Remaining</div>
          <div className="kpi-value">{progress.pending || 0}</div>
        </div>
        <div className="kpi-card">
          <PhoneCall size={20} className="kpi-icon" />
          <div className="kpi-label">Active Calls</div>
          <div className="kpi-value" style={{ color: 'var(--accent-purple)' }}>{progress.calling || 0}</div>
        </div>
        <div className="kpi-card">
          <CheckCircle size={20} className="kpi-icon" />
          <div className="kpi-label">Completed</div>
          <div className="kpi-value" style={{ color: 'var(--accent-green)' }}>{progress.completed || 0}</div>
        </div>
        <div className="kpi-card">
          <PhoneOff size={20} className="kpi-icon" />
          <div className="kpi-label">No Answer</div>
          <div className="kpi-value" style={{ color: 'var(--accent-yellow)' }}>{progress.no_answer || 0}</div>
        </div>
        <div className="kpi-card">
          <AlertCircle size={20} className="kpi-icon" />
          <div className="kpi-label">Failed</div>
          <div className="kpi-value" style={{ color: 'var(--accent-red)' }}>{progress.failed || 0}</div>
        </div>
        <div className="kpi-card">
          <ShieldOff size={20} className="kpi-icon" />
          <div className="kpi-label">DNC / Excluded</div>
          <div className="kpi-value">{progress.dnc || 0}</div>
        </div>
      </div>

      <div className="campaign-layout">
        <div className="card" style={{ padding: 0, border: 'none', background: 'transparent' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-md)' }}>
            <h2 style={{ margin: 0, fontSize: 'var(--font-size-lg)' }}>Audience</h2>
            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)' }}>
              {audience.length} contact{audience.length !== 1 ? 's' : ''}
            </div>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Phone</th>
                  <th>Status</th>
                  <th>Context</th>
                  {campaign.status === 'DRAFT' && <th>Action</th>}
                </tr>
              </thead>
              <tbody>
                {audience.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--text-muted)' }}>
                      No audience members found.
                    </td>
                  </tr>
                ) : (
                  audience.map(a => (
                    <tr key={a.id}>
                      <td style={{ fontWeight: 500 }}>{a.customers?.name || '-'}</td>
                      <td style={{ color: 'var(--text-secondary)' }}>{a.customers?.phone}</td>
                      <td>
                        <span className={getStatusBadgeClass(a.status)}>
                          {a.status}
                        </span>
                      </td>
                      <td>
                        <div className="truncate" title={a.customer_context || ''}>
                          {a.customer_context || '-'}
                        </div>
                      </td>
                      {campaign.status === 'DRAFT' && (
                        <td>
                          <button className="btn btn-danger" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => handleRemoveContact(a.id)}>Remove</button>
                        </td>
                      )}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <h2 style={{ margin: '0 0 var(--space-lg) 0', fontSize: 'var(--font-size-lg)' }}>Recent Activity</h2>
          <div className="timeline-container">
            {activities.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-sm)' }}>No activity yet.</div>
            ) : (
              activities.map(a => (
                <div key={a.id} className="timeline-item">
                  <div className="timeline-dot"></div>
                  <div className="timeline-content">
                    <div className="timeline-title">{a.event_type.replace(/_/g, ' ')}</div>
                    <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-secondary)', margin: '4px 0' }}>{a.message}</div>
                    <div className="timeline-time">{new Date(a.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
