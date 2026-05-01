import axios from 'axios'
import { useEffect, useState } from 'react'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const [activeJobs, setActiveJobs] = useState([])
  const [spools, setSpools] = useState([])
  const [totals, setTotals] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      axios.get('/api/jobs', { params: { status: 'running', page_size: 50 } }),
      axios.get('/api/spools'),
      axios.get('/api/costs/summary/totals'),
    ])
      .then(([jobsRes, spoolsRes, totalsRes]) => {
        setActiveJobs(jobsRes.data)
        setSpools(spoolsRes.data)
        setTotals(totalsRes.data)
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className={styles.state}>Loading…</p>
  if (error) return <p className={styles.error}>Error: {error}</p>

  const totalFilamentKg = spools.reduce((s, sp) => s + sp.weight_remaining_g, 0) / 1000

  return (
    <div>
      <h1>Dashboard</h1>

      <div className={styles.cards}>
        <div className={styles.card}>
          <div className={styles.label}>Active Prints</div>
          <div className={styles.value}>{activeJobs.length}</div>
        </div>
        <div className={styles.card}>
          <div className={styles.label}>Filament on Hand</div>
          <div className={styles.value}>{totalFilamentKg.toFixed(2)} kg</div>
        </div>
        <div className={styles.card}>
          <div className={styles.label}>Completed Jobs</div>
          <div className={styles.value}>{totals?.job_count ?? 0}</div>
        </div>
        <div className={styles.card}>
          <div className={styles.label}>All-Time Print Cost</div>
          <div className={styles.value}>${(totals?.total_cost ?? 0).toFixed(2)}</div>
        </div>
      </div>

      <h2>Active Jobs</h2>
      {activeJobs.length === 0 ? (
        <p className={styles.empty}>No printers are currently printing.</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Printer</th>
              <th>File</th>
              <th>Started</th>
              <th>Filament (g)</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {activeJobs.map(job => (
              <tr key={job.id}>
                <td>{job.id}</td>
                <td>{job.printer_id}</td>
                <td title={job.gcode_filename}>
                  {job.gcode_filename
                    ? job.gcode_filename.length > 28
                      ? job.gcode_filename.slice(0, 28) + '…'
                      : job.gcode_filename
                    : '—'}
                </td>
                <td>{new Date(job.started_at + 'Z').toLocaleString()}</td>
                <td>{job.filament_used_g != null ? job.filament_used_g.toFixed(1) : '—'}</td>
                <td><span className={`${styles.badge} ${styles[job.status]}`}>{job.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
