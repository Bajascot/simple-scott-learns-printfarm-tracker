import axios from 'axios'
import { useEffect, useState } from 'react'
import styles from './Jobs.module.css'

const PAGE_SIZE = 20

function duration(job) {
  if (!job.ended_at) return '—'
  const seconds = (new Date(job.ended_at + 'Z') - new Date(job.started_at + 'Z')) / 1000
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

function truncate(str, n) {
  if (!str) return '—'
  return str.length > n ? str.slice(0, n) + '…' : str
}

export default function Jobs() {
  const [jobs, setJobs] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    axios.get('/api/jobs', { params: { page, page_size: PAGE_SIZE } })
      .then(r => {
        setJobs(r.data)
        setHasMore(r.data.length === PAGE_SIZE)
      })
      .finally(() => setLoading(false))
  }, [page])

  return (
    <div>
      <h1>Print History</h1>

      {loading ? (
        <p style={{ color: '#64748b' }}>Loading…</p>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>#</th>
              <th>Printer</th>
              <th>Spool</th>
              <th>File</th>
              <th>Status</th>
              <th>Started</th>
              <th>Duration</th>
              <th>Filament (g)</th>
              <th>Energy (kWh)</th>
              <th>Total Cost</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map(job => (
              <tr key={job.id}>
                <td>{job.id}</td>
                <td>{job.printer_id}</td>
                <td>{job.spool_id ?? '—'}</td>
                <td title={job.gcode_filename}>{truncate(job.gcode_filename, 22)}</td>
                <td><span className={`${styles.badge} ${styles[job.status]}`}>{job.status}</span></td>
                <td>{new Date(job.started_at + 'Z').toLocaleString()}</td>
                <td>{duration(job)}</td>
                <td>{job.filament_used_g != null ? job.filament_used_g.toFixed(1) : '—'}</td>
                <td>{job.energy_kwh != null ? job.energy_kwh.toFixed(4) : '—'}</td>
                <td>{job.total_cost != null ? `$${job.total_cost.toFixed(2)}` : '—'}</td>
              </tr>
            ))}
            {jobs.length === 0 && (
              <tr><td colSpan={10} style={{ color: '#64748b', textAlign: 'center' }}>No print jobs recorded yet.</td></tr>
            )}
          </tbody>
        </table>
      )}

      <div className={styles.pagination}>
        <button disabled={page === 1} onClick={() => setPage(p => p - 1)}>Previous</button>
        <span>Page {page}</span>
        <button disabled={!hasMore} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>
    </div>
  )
}
