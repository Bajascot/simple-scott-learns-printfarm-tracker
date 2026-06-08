import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import Printers from './pages/Printers'
import Purchases from './pages/Purchases'
import Settings from './pages/Settings'
import Spools from './pages/Spools'
import styles from './App.module.css'

export default function App() {
  return (
    <BrowserRouter>
      <div className={styles.layout}>
        <nav className={styles.nav}>
          <span className={styles.logo}>PrintFarm</span>
          <NavLink to="/" end className={({ isActive }) => isActive ? styles.active : ''}>Dashboard</NavLink>
          <NavLink to="/spools" className={({ isActive }) => isActive ? styles.active : ''}>Spools</NavLink>
          <NavLink to="/printers" className={({ isActive }) => isActive ? styles.active : ''}>Printers</NavLink>
          <NavLink to="/jobs" className={({ isActive }) => isActive ? styles.active : ''}>Jobs</NavLink>
          <NavLink to="/purchases" className={({ isActive }) => isActive ? styles.active : ''}>Purchases</NavLink>
          <NavLink to="/settings" className={({ isActive }) => isActive ? styles.active : ''}>Settings</NavLink>
        </nav>
        <main className={styles.main}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/spools" element={<Spools />} />
            <Route path="/printers" element={<Printers />} />
            <Route path="/jobs" element={<Jobs />} />
            <Route path="/purchases" element={<Purchases />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
