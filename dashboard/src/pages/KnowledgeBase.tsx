import { useEffect, useState } from 'react'
import { api, type KnowledgeRecord, type PaginatedResponse } from '../api/client'

export default function KnowledgeBase() {
  const [data, setData] = useState<PaginatedResponse<KnowledgeRecord> | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [accessLevel, setAccessLevel] = useState('')
  const [page, setPage] = useState(1)

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [editingRecord, setEditingRecord] = useState<Partial<KnowledgeRecord> | null>(null)

  useEffect(() => { loadData() }, [search, accessLevel, page])

  async function loadData() {
    setLoading(true)
    try { setData(await api.getKnowledge({ search: search || undefined, access_level: accessLevel || undefined, page })) }
    catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!editingRecord) return
    try {
      if (editingRecord.id) await api.updateKnowledge(editingRecord.id, editingRecord)
      else await api.createKnowledge(editingRecord)
      setShowModal(false)
      loadData()
    } catch (e) { alert('Failed to save record: ' + e) }
  }

  function openEdit(record: KnowledgeRecord) {
    setEditingRecord({ ...record })
    setShowModal(true)
  }

  function openCreate() {
    setEditingRecord({ category: '', title: '', content: '', access_level: 'PUBLIC', priority: 0 })
    setShowModal(true)
  }

  async function toggleActive(record: KnowledgeRecord) {
    try {
      await api.updateKnowledge(record.id, { is_active: !record.is_active })
      loadData()
    } catch (e) { alert('Failed to update status') }
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 0

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Knowledge Base</h1>
          <p className="page-subtitle">{data?.total ?? 0} records across all access levels</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Add Record</button>
      </div>

      <div className="filter-bar">
        <input className="input" style={{ maxWidth: 300 }} placeholder="Search title, content, category..." value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} />
        <select className="select" value={accessLevel} onChange={e => { setAccessLevel(e.target.value); setPage(1) }}>
          <option value="">All Access Levels</option>
          <option value="PUBLIC">PUBLIC</option>
          <option value="INTERNAL">INTERNAL</option>
          <option value="RESTRICTED">RESTRICTED</option>
        </select>
      </div>

      {loading ? <div className="loading"><div className="spinner" />Loading...</div> : (
        <div className="table-container">
          <table>
            <thead><tr><th>Title / Category</th><th>Content Preview</th><th>Access</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {data?.data.map(r => (
                <tr key={r.id}>
                  <td onClick={() => openEdit(r)}>
                    <div style={{ fontWeight: 600 }}>{r.title}</div>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{r.category}</div>
                  </td>
                  <td onClick={() => openEdit(r)} style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.content}</td>
                  <td><span className={`badge ${r.access_level.toLowerCase()}`}>{r.access_level}</span></td>
                  <td>
                    <button className={`badge ${r.is_active ? 'active' : 'inactive'}`} style={{ border: 'none', cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); toggleActive(r); }}>
                      {r.is_active ? 'Active' : 'Inactive'}
                    </button>
                  </td>
                  <td><button className="btn btn-secondary" onClick={() => openEdit(r)}>Edit</button></td>
                </tr>
              ))}
              {data?.data.length === 0 && <tr><td colSpan={5}><div className="empty-state"><div className="empty-state-text">No knowledge records found</div></div></td></tr>}
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

      {showModal && editingRecord && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2 className="modal-title">{editingRecord.id ? 'Edit Knowledge Record' : 'Create Knowledge Record'}</h2>
            <form onSubmit={handleSave}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <input required className="input" value={editingRecord.category || ''} onChange={e => setEditingRecord({ ...editingRecord, category: e.target.value })} />
                </div>
                <div className="form-group">
                  <label className="form-label">Access Level</label>
                  <select className="select" style={{ width: '100%' }} value={editingRecord.access_level || 'PUBLIC'} onChange={e => setEditingRecord({ ...editingRecord, access_level: e.target.value })}>
                    <option value="PUBLIC">PUBLIC</option>
                    <option value="INTERNAL">INTERNAL</option>
                    <option value="RESTRICTED">RESTRICTED</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Title</label>
                <input required className="input" value={editingRecord.title || ''} onChange={e => setEditingRecord({ ...editingRecord, title: e.target.value })} />
              </div>

              <div className="form-group">
                <label className="form-label">Content</label>
                <textarea required className="input" style={{ minHeight: 160 }} value={editingRecord.content || ''} onChange={e => setEditingRecord({ ...editingRecord, content: e.target.value })} />
              </div>

              <div className="form-group">
                <label className="form-label">Keywords (comma separated)</label>
                <input className="input" value={editingRecord.keywords || ''} onChange={e => setEditingRecord({ ...editingRecord, keywords: e.target.value })} />
              </div>

              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Record</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
