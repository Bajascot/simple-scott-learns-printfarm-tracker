import axios from 'axios'
import { useEffect, useState } from 'react'
import styles from './Printers.module.css'

const EMPTY = { name: '', model: '', moonraker_url: 'http://192.168.1.100', govee_device_id: '', notes: '' }

export default function Printers() {
  const [printers, setPrinters] = useState([])
  const [statuses, setStatuses] = useState({})
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [saving, setSaving] = useState(false)
  const [goveeDevices, setGoveeDevices] = useState(null)  // null=loading, []+=loaded
  const [goveeConfigured, setGoveeConfigured] = useState(false)

  const load = () => axios.get('/api/printers').then(r => setPrinters(r.data))
  useEffect(() => { load() }, [])

  useEffect(() => {
    printers.forEach(p => {
      setStatuses(prev => ({ ...prev, [p.id]: 'checking' }))
      axios.get(`/api/printers/${p.id}`, { timeout: 5000 })
        .then(() => {
          // Moonraker reachability check goes through the FastAPI proxy in dev,
          // so we do a quick /printer/info ping via the moonraker URL directly.
          return fetch(`${p.moonraker_url}/printer/info`, { signal: AbortSignal.timeout(4000) })
        })
        .then(res => setStatuses(prev => ({ ...prev, [p.id]: res.ok ? 'online' : 'offline' })))
        .catch(() => setStatuses(prev => ({ ...prev, [p.id]: 'offline' })))
    })
  }, [printers])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const openModal = (initial, target) => {
    setForm(initial)
    setModal(target)
    setGoveeDevices(null)
    axios.get('/api/govee/status').then(r => {
      setGoveeConfigured(r.data.configured)
      if (r.data.configured) {
        axios.get('/api/govee/devices')
          .then(r => setGoveeDevices(r.data))
          .catch(() => setGoveeDevices([]))
      } else {
        setGoveeDevices([])
      }
    }).catch(() => setGoveeDevices([]))
  }

  const openAdd = () => openModal(EMPTY, 'add')
  const openEdit = (p) => openModal({ ...p }, p)
  const close = () => setModal(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (modal === 'add') {
        await axios.post('/api/printers', form)
      } else {
        await axios.patch(`/api/printers/${modal.id}`, form)
      }
      await load()
      close()
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this printer?')) return
    await axios.delete(`/api/printers/${id}`)
    await load()
  }

  return (
    <div>
      <div className={styles.header}>
        <h1>Printers</h1>
        <button className={styles.btn} onClick={openAdd}>+ Add Printer</button>
      </div>

      <div className={styles.grid}>
        {printers.map(p => {
          const st = statuses[p.id]
          const goveeLabel = p.govee_device_id
            ? (goveeDevices || []).find(d => d.device === p.govee_device_id)?.deviceName || p.govee_device_id
            : null
          return (
            <div key={p.id} className={styles.card}>
              <div className={styles.cardTop}>
                <span className={`${styles.dot} ${st === 'online' ? styles.online : st === 'offline' ? styles.offline : styles.checking}`} />
                <span className={styles.statusText}>{st || 'unknown'}</span>
              </div>
              <h3 className={styles.name}>{p.name}</h3>
              <p className={styles.model}>{p.model}</p>
              <p className={styles.url}>{p.moonraker_url}</p>
              {goveeLabel && <p className={styles.govee}>⚡ {goveeLabel}</p>}
              {p.notes && <p className={styles.notes}>{p.notes}</p>}
              <div className={styles.cardActions}>
                <button className={styles.btnSm} onClick={() => openEdit(p)}>Edit</button>
                <button className={`${styles.btnSm} ${styles.danger}`} onClick={() => handleDelete(p.id)}>Delete</button>
              </div>
            </div>
          )
        })}
        {printers.length === 0 && <p style={{ color: '#64748b' }}>No printers yet.</p>}
      </div>

      {modal && (
        <div className={styles.overlay} onClick={e => e.target === e.currentTarget && close()}>
          <div className={styles.dialog}>
            <h2>{modal === 'add' ? 'Add Printer' : 'Edit Printer'}</h2>
            <form onSubmit={handleSubmit} className={styles.form}>
              <label>Name <input value={form.name} onChange={e => set('name', e.target.value)} required /></label>
              <label>Model <input value={form.model} onChange={e => set('model', e.target.value)} placeholder="e.g. Voron 2.4, Bambu X1C" required /></label>
              <label>Moonraker URL <input value={form.moonraker_url} onChange={e => set('moonraker_url', e.target.value)} placeholder="http://192.168.1.100" required /></label>
              <label>
                Govee Smart Plug
                {goveeDevices === null ? (
                  <input disabled placeholder="Loading devices…" />
                ) : !goveeConfigured ? (
                  <input disabled placeholder="Set GOVEE_API_KEY in .env to enable" />
                ) : goveeDevices.length === 0 ? (
                  <input disabled placeholder="No devices found on your Govee account" />
                ) : (
                  <select value={form.govee_device_id || ''} onChange={e => set('govee_device_id', e.target.value)}>
                    <option value="">— None —</option>
                    {goveeDevices.map(d => (
                      <option key={d.device} value={d.device}>{d.deviceName} ({d.model})</option>
                    ))}
                  </select>
                )}
              </label>
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
