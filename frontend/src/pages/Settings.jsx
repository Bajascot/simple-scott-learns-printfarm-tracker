import axios from 'axios'
import { useEffect, useState } from 'react'
import styles from './Settings.module.css'

export default function Settings() {
  const [energyRate, setEnergyRate] = useState('0.12')
  const [goveeKey, setGoveeKey] = useState('')
  const [watchDir, setWatchDir] = useState('/home/pi/slicer-output')
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    axios.get('/api/costs/energy-rates')
      .then(r => {
        if (r.data.length > 0) setEnergyRate(String(r.data[0].rate_per_kwh))
      })
      .catch(() => {})
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const rate = parseFloat(energyRate)
      if (!isNaN(rate) && rate > 0) {
        await axios.post('/api/costs/energy-rates', {
          rate_per_kwh: rate,
          effective_from: new Date().toISOString().slice(0, 10),
          label: 'Updated via Settings page',
        })
      }
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={styles.container}>
      <h1>Settings</h1>
      <form onSubmit={handleSave} className={styles.form}>

        <fieldset className={styles.fieldset}>
          <legend>Energy Pricing</legend>
          <label>
            Rate per kWh ($)
            <input
              type="number"
              step="0.001"
              min="0"
              value={energyRate}
              onChange={e => setEnergyRate(e.target.value)}
              required
            />
            <span className={styles.hint}>Used to calculate energy cost per print job.</span>
          </label>
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend>Govee Smart Plug Integration</legend>
          <label>
            Govee API Key
            <input
              type="password"
              autoComplete="off"
              placeholder="Paste your Govee Developer API key"
              value={goveeKey}
              onChange={e => setGoveeKey(e.target.value)}
            />
          </label>
          <p className={styles.hint}>
            Get your key from the Govee Home app: Profile → About Us → Apply for API Key.
            Set <code>GOVEE_API_KEY</code> in your <code>.env</code> file and restart the server to activate polling.
          </p>
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend>Slicer File Watcher</legend>
          <label>
            Watched Folder Path
            <input
              value={watchDir}
              onChange={e => setWatchDir(e.target.value)}
              placeholder="/home/pi/slicer-output"
            />
          </label>
          <p className={styles.hint}>
            Drop <code>.gcode</code> or <code>.3mf</code> files here and a draft job record will be created
            automatically with the estimated filament weight pre-filled.
            Update <code>SLICER_WATCH_DIR</code> in <code>.env</code> and restart to change the watched directory.
          </p>
        </fieldset>

        <div className={styles.footer}>
          <button type="submit" className={styles.btn} disabled={saving}>
            {saving ? 'Saving…' : 'Save Settings'}
          </button>
          {saved && <span className={styles.saved}>Saved!</span>}
        </div>
      </form>
    </div>
  )
}
