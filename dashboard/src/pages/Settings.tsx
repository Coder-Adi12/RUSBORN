import { useEffect, useState } from 'react'
import { api, type AgentSettings, type AgentSettingsUpdate, type SystemHealth } from '../api/client'

const DAYS: { n: number; label: string }[] = [
  { n: 1, label: 'Mon' },
  { n: 2, label: 'Tue' },
  { n: 3, label: 'Wed' },
  { n: 4, label: 'Thu' },
  { n: 5, label: 'Fri' },
  { n: 6, label: 'Sat' },
  { n: 7, label: 'Sun' },
]

const COMMON_TIMEZONES = [
  'Asia/Kolkata', 'UTC', 'America/New_York', 'America/Los_Angeles',
  'Europe/London', 'Europe/Berlin', 'Asia/Dubai', 'Asia/Singapore',
  'Australia/Sydney',
]

function fromSettings(s: AgentSettings): AgentSettingsUpdate {
  return {
    appointment_timezone: s.appointment_timezone,
    appointment_duration_minutes: s.appointment_duration_minutes,
    appointment_working_days: [...s.appointment_working_days],
    appointment_start_time: s.appointment_start_time,
    appointment_end_time: s.appointment_end_time,
  }
}

export default function Settings() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(true)

  const [settings, setSettings] = useState<AgentSettings | null>(null)
  const [form, setForm] = useState<AgentSettingsUpdate>({})
  const [settingsLoading, setSettingsLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ type: 'ok' | 'error'; text: string } | null>(null)

  useEffect(() => {
    api.getHealth().then(setHealth).catch(console.error).finally(() => setLoading(false))
    loadSettings()
  }, [])

  function loadSettings() {
    setSettingsLoading(true)
    api.getAgentSettings()
      .then(s => { setSettings(s); setForm(fromSettings(s)) })
      .catch(console.error)
      .finally(() => setSettingsLoading(false))
  }

  function toggleDay(n: number) {
    const cur = form.appointment_working_days ?? []
    const next = cur.includes(n) ? cur.filter(d => d !== n) : [...cur, n]
    next.sort((a, b) => a - b)
    setForm({ ...form, appointment_working_days: next })
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaveMsg(null)
    const days = form.appointment_working_days ?? []
    if (days.length === 0) {
      setSaveMsg({ type: 'error', text: 'Select at least one working day.' })
      return
    }
    if ((form.appointment_start_time ?? '') >= (form.appointment_end_time ?? '')) {
      setSaveMsg({ type: 'error', text: 'Start time must be earlier than end time.' })
      return
    }
    setSaving(true)
    try {
      const updated = await api.updateAgentSettings(form)
      setSettings(updated)
      setForm(fromSettings(updated))
      setSaveMsg({ type: 'ok', text: 'Settings saved. The agent will use these on the next call.' })
    } catch (err) {
      setSaveMsg({ type: 'error', text: 'Failed to save: ' + (err instanceof Error ? err.message : String(err)) })
    } finally {
      setSaving(false)
    }
  }

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
          <h3 style={{ marginBottom: 'var(--space-sm)', fontSize: 'var(--font-size-md)' }}>Agent Configuration</h3>
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-md)' }}>
            Editing these updates the booking window used by both the backend and the voice agent.
          </p>
          {settingsLoading ? <div className="loading"><div className="spinner" />Loading...</div> : settings ? (
            <form onSubmit={handleSave}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
                <div className="form-group">
                  <label className="form-label">Appointment Duration (minutes)</label>
                  <input type="number" min={5} max={480} required className="input"
                    value={form.appointment_duration_minutes ?? ''}
                    onChange={e => setForm({ ...form, appointment_duration_minutes: e.target.value === '' ? undefined : Number(e.target.value) })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Timezone</label>
                  <input required className="input" list="tz-options"
                    value={form.appointment_timezone ?? ''}
                    onChange={e => setForm({ ...form, appointment_timezone: e.target.value })} />
                  <datalist id="tz-options">
                    {COMMON_TIMEZONES.map(tz => <option key={tz} value={tz} />)}
                  </datalist>
                </div>
                <div className="form-group">
                  <label className="form-label">Start Time</label>
                  <input type="time" required className="input"
                    value={form.appointment_start_time ?? ''}
                    onChange={e => setForm({ ...form, appointment_start_time: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">End Time</label>
                  <input type="time" required className="input"
                    value={form.appointment_end_time ?? ''}
                    onChange={e => setForm({ ...form, appointment_end_time: e.target.value })} />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Working Days</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
                  {DAYS.map(d => {
                    const active = (form.appointment_working_days ?? []).includes(d.n)
                    return (
                      <button type="button" key={d.n}
                        className={`badge ${active ? 'active' : 'inactive'}`}
                        style={{ border: 'none', cursor: 'pointer' }}
                        onClick={() => toggleDay(d.n)}>
                        {d.label}
                      </button>
                    )
                  })}
                </div>
              </div>

              {saveMsg && (
                <div style={{ marginBottom: 'var(--space-md)', fontSize: 'var(--font-size-sm)', color: saveMsg.type === 'ok' ? '#16a34a' : '#dc2626' }}>
                  {saveMsg.text}
                </div>
              )}

              <div className="form-actions">
                <button type="button" className="btn btn-secondary" disabled={saving} onClick={() => settings && setForm(fromSettings(settings))}>Reset</button>
                <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</button>
              </div>
              {settings.updated_at && (
                <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', marginTop: 'var(--space-sm)' }}>
                  Last updated: {new Date(settings.updated_at).toLocaleString()}
                </p>
              )}
            </form>
          ) : <div className="empty-state">Failed to load agent settings</div>}
        </div>
      </div>
    </div>
  )
}
