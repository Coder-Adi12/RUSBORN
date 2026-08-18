import { useEffect, useState } from 'react'
import { api, type SystemHealth } from '../api/client'

export default function Settings() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Settings & System Health</h1>
        <p className="page-subtitle">Platform configuration and live status</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
        <div className="card">
          <h3 style={{ marginBottom: 'var(--space-md)', fontSize: 'var(--font-size-md)' }}>System Health</h3>
          {loading ? <div className="loading"><div className="spinner" />Checking...</div> : health ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 'var(--space-sm)', borderBottom: '1px solid var(--border-secondary)' }}>
                <span style={{ fontWeight: 500 }}>Dashboard API</span>
                <span className={`badge ${health.api.status === 'healthy' ? 'healthy' : 'error'}`}>{health.api.status.toUpperCase()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 'var(--space-sm)', borderBottom: '1px solid var(--border-secondary)' }}>
                <span style={{ fontWeight: 500 }}>Supabase Database</span>
                <span className={`badge ${health.database.status === 'healthy' ? 'healthy' : 'error'}`}>{health.database.status.toUpperCase()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 'var(--space-sm)', borderBottom: '1px solid var(--border-secondary)' }}>
                <span style={{ fontWeight: 500 }}>Knowledge Base Search (RPC)</span>
                <span className={`badge ${health.knowledge_search.status === 'healthy' ? 'healthy' : 'error'}`}>{health.knowledge_search.status.toUpperCase()}</span>
              </div>
            </div>
          ) : <div className="empty-state">Health check failed</div>}
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 'var(--space-md)', fontSize: 'var(--font-size-md)' }}>Agent Configuration (Read-only)</h3>
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-md)' }}>
            These settings are defined in the backend environment variables.
          </p>
          <div className="detail-row"><span className="detail-label">Appointment Duration</span><span className="detail-value">30 mins</span></div>
          <div className="detail-row"><span className="detail-label">Working Hours</span><span className="detail-value">09:00 - 18:00</span></div>
          <div className="detail-row"><span className="detail-label">Timezone</span><span className="detail-value">Asia/Kolkata</span></div>
          <div className="detail-row"><span className="detail-label">Working Days</span><span className="detail-value">Mon-Fri (1,2,3,4,5)</span></div>
        </div>
      </div>
    </div>
  )
}
