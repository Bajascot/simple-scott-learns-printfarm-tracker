import axios from 'axios'
import { useEffect, useState } from 'react'
import styles from './Spools.module.css'

const MATERIALS = ['PLA', 'PETG', 'ABS', 'TPU', 'ASA', 'Other']
const EMPTY = { brand: '', material: 'PLA', color: '', weight_total_g: 1000, weight_remaining_g: 1000, cost_total: 25, purchase_date: '', notes: '' }

export default function Spools() {
  const [spools, setSpools] = useState([])
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)

  const load = () => axios.get('/api/spools').then(r => setSpools(r.data))
  useEffect(() => { load() }, [])

  const openAdd = () => { setForm(EMPTY); setModal('add') }
  const openEdit = (s) => { setForm({ ...s, purchase_date: s.purchase_date || '' }); setModal(s) }
  const close = () => setModal(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    const payload = { ...form }
    if (!payload.purchase_date) delete payload.purchase_date
    try {
      if (modal === 'add') {
        await axios.post('/api/spools', payload)
      } else {
        await axios.patch(`/api/spools/${modal.id}`, payload)
      }
      await load()
      close()
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this spool? This cannot be undone.')) return
    await axios.delete(`/api/spools/${id}`)
    await load()
  }

  return (
    <div>
      <div className={styles.header}>
        <h1>Filament Spools</h1>
        <button className={styles.btn} onClick={openAdd}>+ Add Spool</button>
      </div>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>Brand</th>
            <th>Material</th>
            <th>Color</th>
            <th>Remaining</th>
            <th>Cost</th>
            <th>Purchased</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {spools.map(s => {
            const pct = s.weight_total_g > 0 ? (s.weight_remaining_g / s.weight_total_g) * 100 : 0
            const low = pct < 20
            return (
              <tr key={s.id}>
                <td>{s.brand}</td>
                <td>{s.material}</td>
                <td>
                  <span className={styles.swatch} style={{ background: s.color.toLowerCase() }} />
                  {s.color}
                </td>
                <td>
                  <div className={styles.progressWrap}>
                    <div
                      className={`${styles.progressBar} ${low ? styles.low : ''}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className={styles.progressLabel}>
                    {s.weight_remaining_g.toFixed(0)} g / {s.weight_total_g.toFixed(0)} g
                  </span>
                </td>
                <td>${s.cost_total.toFixed(2)}</td>
                <td>{s.purchase_date || '—'}</td>
                <td>
                  <button className={styles.btnSm} onClick={() => openEdit(s)}>Edit</button>
                  <button className={`${styles.btnSm} ${styles.danger}`} onClick={() => handleDelete(s.id)}>Delete</button>
                </td>
              </tr>
            )
          })}
          {spools.length === 0 && (
            <tr><td colSpan={7} style={{ color: '#64748b', textAlign: 'center' }}>No spools yet. Add one above.</td></tr>
          )}
        </tbody>
      </table>

      {modal && (
        <div className={styles.overlay} onClick={e => e.target === e.currentTarget && close()}>
          <div className={styles.dialog}>
            <h2>{modal === 'add' ? 'Add Spool' : 'Edit Spool'}</h2>
            <form onSubmit={handleSubmit} className={styles.form}>
              <label>Brand <input value={form.brand} onChange={e => set('brand', e.target.value)} required /></label>
              <label>Material
                <select value={form.material} onChange={e => set('material', e.target.value)}>
                  {MATERIALS.map(m => <option key={m}>{m}</option>)}
                </select>
              </label>
              <label>Color <input value={form.color} onChange={e => set('color', e.target.value)} placeholder="e.g. red, #1a2b3c" required /></label>
              <div className={styles.row}>
                <label>Total Weight (g)
                  <input type="number" value={form.weight_total_g} onChange={e => set('weight_total_g', +e.target.value)} min={0} step={1} required />
                </label>
                <label>Remaining (g)
                  <input type="number" value={form.weight_remaining_g} onChange={e => set('weight_remaining_g', +e.target.value)} min={0} step={1} required />
                </label>
              </div>
              <label>Cost ($) <input type="number" step="0.01" value={form.cost_total} onChange={e => set('cost_total', +e.target.value)} min={0} required /></label>
              <label>Purchase Date <input type="date" value={form.purchase_date} onChange={e => set('purchase_date', e.target.value)} /></label>
              <label>Notes <textarea value={form.notes || ''} onChange={e => set('notes', e.target.value)} rows={2} /></label>
              <div className={styles.actions}>
                <button type="button" onClick={close}>Cancel</button>
                <button type="submit" className={styles.btn} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
