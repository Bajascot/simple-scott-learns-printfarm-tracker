import axios from 'axios'
import { useEffect, useRef, useState } from 'react'
import styles from './Purchases.module.css'

export default function Purchases() {
  const [purchases, setPurchases] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const fileRef = useRef(null)

  const load = () => {
    setLoading(true)
    axios.get('/api/purchases')
      .then(r => setPurchases(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleUpload = async (e) => {
    e.preventDefault()
    const file = fileRef.current?.files[0]
    if (!file) return
    setUploading(true)
    setResult(null)
    setError(null)
    const form = new FormData()
    form.append('file', file)
    try {
      const r = await axios.post('/api/purchases/import/amazon-csv', form)
      setResult(r.data)
      if (r.data.inserted > 0) load()
    } catch {
      setError('Import failed — make sure you uploaded the correct Amazon order history CSV.')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const totalSpend = purchases.reduce((sum, p) => sum + p.cost, 0)

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Purchases</h1>
        <span className={styles.total}>${totalSpend.toFixed(2)} total</span>
      </div>

      <div className={styles.importBox}>
        <h2>Import from Amazon</h2>
        <p className={styles.hint}>
          Download your order history from{' '}
          <strong>Amazon &rarr; Account &rarr; Order History Reports</strong>, then
          upload the CSV below. Only filament purchases are imported; duplicates are skipped.
        </p>
        <form onSubmit={handleUpload} className={styles.uploadRow}>
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            required
            className={styles.fileInput}
          />
          <button type="submit" className={styles.btn} disabled={uploading}>
            {uploading ? 'Importing…' : 'Import CSV'}
          </button>
        </form>
        {result && (
          <p className={styles.success}>
            Done — {result.inserted} new purchase{result.inserted !== 1 ? 's' : ''} added,{' '}
            {result.skipped} duplicate{result.skipped !== 1 ? 's' : ''} skipped
            {' '}({result.total_found} filament rows found in file).
          </p>
        )}
        {error && <p className={styles.errorMsg}>{error}</p>}
      </div>

      {loading ? (
        <p>Loading…</p>
      ) : purchases.length === 0 ? (
        <p className={styles.empty}>No purchases yet — import an Amazon CSV to get started.</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Date</th>
              <th>Item</th>
              <th>Order ID</th>
              <th style={{ textAlign: 'right' }}>Cost</th>
            </tr>
          </thead>
          <tbody>
            {purchases.map(p => (
              <tr key={p.id}>
                <td className={styles.date}>{p.purchase_date}</td>
                <td>{p.item_name}</td>
                <td className={styles.orderId}>{p.amazon_order_id || '—'}</td>
                <td style={{ textAlign: 'right' }}>${p.cost.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
