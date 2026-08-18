import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { campaignsApi, type Campaign } from '../api/client'

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    campaignsApi.listCampaigns().then(data => {
      setCampaigns(data)
      setLoading(false)
    }).catch(err => {
      console.error(err)
      setLoading(false)
    })
  }, [])

  if (loading) return <div className="loading">Loading campaigns...</div>

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Campaigns</h1>
          <p className="page-subtitle">Outbound bulk calling and lead management</p>
        </div>
        <Link to="/campaigns/new" className="button button-primary">Create Campaign</Link>
      </div>

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Campaign Name</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', padding: '2rem' }}>No campaigns found.</td>
              </tr>
            ) : (
              campaigns.map(c => (
                <tr key={c.id}>
                  <td><strong>{c.name}</strong></td>
                  <td>
                    <span className={`status-badge status-${c.status.toLowerCase()}`}>
                      {c.status}
                    </span>
                  </td>
                  <td>{new Date(c.created_at).toLocaleDateString()}</td>
                  <td>
                    <Link to={`/campaigns/${c.id}`} className="button button-secondary button-sm">View Detail</Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
