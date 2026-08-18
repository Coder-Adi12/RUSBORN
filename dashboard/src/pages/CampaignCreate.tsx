import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { campaignsApi, type Campaign } from '../api/client'
import { UploadCloud, CheckCircle2, ChevronRight, FileText } from 'lucide-react'

export default function CampaignCreate() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Campaign Info
  const [formData, setFormData] = useState<Partial<Campaign>>({
    name: '',
    objective: '',
    voice_agent_instructions: '',
    timezone: 'Asia/Kolkata',
    max_concurrent_calls: 1,
    max_attempts_per_customer: 1,
    retry_delay_minutes: 30
  })

  // File Upload State
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [headers, setHeaders] = useState<string[]>([])
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [preview, setPreview] = useState<any[]>([])
  const [totalRows, setTotalRows] = useState(0)
  
  // Created campaign ID to associate audience with
  const [campaignId, setCampaignId] = useState<string | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const value = e.target.type === 'number' ? parseInt(e.target.value) : e.target.value
    setFormData({ ...formData, [e.target.name]: value })
  }

  const handleMappingChange = (field: string, csvHeader: string) => {
    setMapping({ ...mapping, [field]: csvHeader })
  }

  const handleCreateCampaignInfo = async () => {
    setLoading(true)
    setError(null)
    try {
      const campaign = await campaignsApi.createCampaign(formData)
      setCampaignId(campaign.id)
      setStep(2)
    } catch (err: any) {
      setError(err.message || 'Failed to create campaign')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return
    if (!campaignId) return
    
    setFile(selectedFile)
    setLoading(true)
    setError(null)
    
    try {
      const res = await campaignsApi.uploadAudiencePreview(campaignId, selectedFile)
      setHeaders(res.headers || [])
      setMapping(res.mapping || {})
      setPreview(res.preview || [])
      setTotalRows(res.total_rows || 0)
      setStep(3)
    } catch (err: any) {
      setError(err.message || 'Failed to parse CSV file')
    } finally {
      setLoading(false)
    }
  }

  const handleImportAudience = async () => {
    if (!campaignId || !file) return
    setLoading(true)
    setError(null)
    try {
      await campaignsApi.importAudience(campaignId, file, mapping)
      navigate(`/campaigns/${campaignId}`)
    } catch (err: any) {
      setError(err.message || 'Failed to import audience')
      setLoading(false)
    }
  }

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault() }
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const dropFile = e.dataTransfer.files[0]
      if (dropFile.name.endsWith('.csv')) {
        const syntheticEvent = {
          target: { files: [dropFile] }
        } as unknown as React.ChangeEvent<HTMLInputElement>
        handleFileUpload(syntheticEvent)
      } else {
        setError("Only CSV files are supported.")
      }
    }
  }

  return (
    <div>
      <div className="page-header" style={{ marginBottom: 'var(--space-2xl)' }}>
        <h1 className="page-title">Create Campaign</h1>
        <p className="page-subtitle">Configure outbound strategy & import audience</p>
      </div>

      <div className="stepper">
        <div className={`stepper-item ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}>
          {step > 1 ? <CheckCircle2 size={20} /> : '01'} Objective
        </div>
        <div className="stepper-separator" />
        <div className={`stepper-item ${step >= 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}>
          {step > 2 ? <CheckCircle2 size={20} /> : '02'} Audience
        </div>
        <div className="stepper-separator" />
        <div className={`stepper-item ${step >= 3 ? 'active' : ''}`}>
          03 Review
        </div>
      </div>

      <div className="card">
        {error && (
          <div style={{ padding: 'var(--space-md)', background: 'var(--accent-red-bg)', color: 'var(--accent-red)', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-lg)' }}>
            {error}
          </div>
        )}
        
        {step === 1 && (
          <div className="form-group-wrap" style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h2 style={{ marginBottom: 'var(--space-lg)' }}>Campaign Configuration</h2>
            <div className="form-group">
              <label className="form-label">Campaign Name</label>
              <input className="input" name="name" value={formData.name || ''} onChange={handleChange} placeholder="e.g. Q3 Reactivation" />
            </div>
            <div className="form-group">
              <label className="form-label">Objective</label>
              <input className="input" name="objective" value={formData.objective || ''} onChange={handleChange} placeholder="Brief objective" />
            </div>
            <div className="form-group">
              <label className="form-label">Voice Agent Instructions</label>
              <textarea className="input" name="voice_agent_instructions" value={formData.voice_agent_instructions || ''} onChange={handleChange} rows={3} placeholder="Specific instructions for this campaign." />
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-lg)', marginTop: 'var(--space-lg)' }}>
              <div className="form-group">
                <label className="form-label">Timezone</label>
                <select className="input" name="timezone" value={formData.timezone} onChange={handleChange}>
                  <option value="Asia/Kolkata">Asia/Kolkata</option>
                  <option value="UTC">UTC</option>
                  <option value="America/New_York">America/New_York</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Max Concurrent Calls</label>
                <input className="input" type="number" name="max_concurrent_calls" value={formData.max_concurrent_calls} onChange={handleChange} min={1} max={10} />
              </div>
              <div className="form-group">
                <label className="form-label">Max Attempts (Per Customer)</label>
                <input className="input" type="number" name="max_attempts_per_customer" value={formData.max_attempts_per_customer} onChange={handleChange} min={1} max={5} />
              </div>
              <div className="form-group">
                <label className="form-label">Retry Delay (minutes)</label>
                <input className="input" type="number" name="retry_delay_minutes" value={formData.retry_delay_minutes} onChange={handleChange} min={5} />
              </div>
            </div>
            
            <div style={{ marginTop: 'var(--space-xl)', display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-primary" onClick={handleCreateCampaignInfo} disabled={loading || !formData.name || !formData.objective}>
                {loading ? 'Saving...' : 'Next Step'} <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="form-group-wrap" style={{ maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
            <h2 style={{ marginBottom: 'var(--space-md)' }}>Upload Audience CSV</h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: 'var(--space-xl)' }}>
              Upload a CSV file containing your contacts. Phone number is required.
            </p>
            
            <input 
              type="file" 
              accept=".csv" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              onChange={handleFileUpload}
            />
            
            <div 
              className="dropzone"
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <UploadCloud size={48} className="dropzone-icon" />
              <div>
                <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 600, color: 'var(--text-primary)' }}>Drop CSV file here</div>
                <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>or click to browse</div>
              </div>
              <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-muted)', marginTop: 'var(--space-sm)' }}>
                {loading ? 'Uploading...' : 'CSV · up to configured limit'}
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="form-group-wrap">
            <h2 style={{ marginBottom: 'var(--space-md)' }}>Review & Map Columns</h2>
            
            <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', background: 'var(--accent-blue-bg)', borderColor: 'var(--accent-blue)', marginBottom: 'var(--space-xl)' }}>
              <FileText size={24} style={{ color: 'var(--accent-blue)' }} />
              <div>
                <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>File parsed successfully</div>
                <div style={{ color: 'var(--accent-blue)', fontSize: 'var(--font-size-sm)' }}>We detected {totalRows} rows in your CSV. Please verify mappings before importing.</div>
              </div>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-lg)', marginBottom: 'var(--space-xl)' }}>
              {['phone', 'name', 'email', 'company', 'description', 'context'].map(field => (
                <div key={field} className="form-group">
                  <label className="form-label" style={{ textTransform: 'capitalize' }}>
                    {field} {field === 'phone' && <span style={{ color: 'var(--accent-red)' }}>*</span>}
                  </label>
                  <select 
                    className="input" 
                    value={mapping[field] || ''} 
                    onChange={(e) => handleMappingChange(field, e.target.value)}
                  >
                    <option value="">-- Ignore --</option>
                    {headers.map(h => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <h3 style={{ marginBottom: 'var(--space-sm)' }}>Data Preview</h3>
            <div className="table-container" style={{ marginBottom: 'var(--space-xl)' }}>
              <table>
                <thead>
                  <tr>
                    {['phone', 'name', 'email', 'company', 'description', 'context'].map(f => (
                      <th key={f}>{f}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.slice(0, 5).map((row, i) => (
                    <tr key={i}>
                      {['phone', 'name', 'email', 'company', 'description', 'context'].map(f => (
                        <td key={f}><div className="truncate">{row[mapping[f] || ''] || '-'}</div></td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ display: 'flex', gap: 'var(--space-md)', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setStep(2)}>Back</button>
              <button 
                className="btn btn-primary" 
                onClick={handleImportAudience} 
                disabled={loading || !mapping.phone}
              >
                {loading ? 'Importing...' : 'Import Audience'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
