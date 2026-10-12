import { useState } from 'react'
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import {
  BarChart3, Cloud, Database, FileImage, History, LayoutDashboard,
  LogOut, Menu, Satellite, Settings, Sparkles, UploadCloud, X
} from 'lucide-react'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Analysis from './pages/Analysis'
import Results from './pages/Results'
import HistoryPage from './pages/History'
import './index.css'

const nav = [
  {to:'/app', label:'Dashboard', icon:LayoutDashboard, end:true},
  {to:'/app/upload', label:'Upload imagery', icon:UploadCloud},
  {to:'/app/analysis', label:'AI analysis', icon:Sparkles},
  {to:'/app/results', label:'Results', icon:FileImage},
  {to:'/app/history', label:'Processing history', icon:History},
]

function Shell() {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const logout = () => { localStorage.removeItem('cloudrecon_token'); navigate('/') }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><Satellite size={21}/></div>
          <div><strong>CloudRecon</strong><span>AI SATELLITE LAB</span></div>
          <button className="icon-btn mobile-close" onClick={()=>setOpen(false)}><X/></button>
        </div>

        <div className="side-label">WORKSPACE</div>
        <nav>
          {nav.map(({to,label,icon:Icon,end}) => (
            <NavLink key={to} to={to} end={end} onClick={()=>setOpen(false)}>
              <Icon size={18}/><span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="side-label">SYSTEM</div>
        <NavLink to="/app/settings" onClick={()=>setOpen(false)}><Settings size={18}/><span>Settings</span></NavLink>

        <div className="sidebar-bottom">
          <div className="storage-card">
            <div className="storage-head"><Database size={15}/> Storage</div>
            <div className="progress"><i style={{width:'38%'}}/></div>
            <small>3.8 GB of 10 GB used</small>
          </div>
          <button className="logout" onClick={logout}><LogOut size={17}/> Sign out</button>
        </div>
      </aside>

      {open && <div className="overlay" onClick={()=>setOpen(false)}/>}
      <main className="main-area">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={()=>setOpen(true)}><Menu/></button>
          <div className="top-search"><Cloud size={16}/><span>Satellite intelligence workspace</span></div>
          <div className="top-user"><div className="avatar">KS</div><div><b>Kundan Suman</b><small>Researcher</small></div></div>
        </header>
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard/>}/>
            <Route path="/upload" element={<Upload/>}/>
            <Route path="/analysis" element={<Analysis/>}/>
            <Route path="/results" element={<Results/>}/>
            <Route path="/history" element={<HistoryPage/>}/>
            <Route path="/settings" element={<div className="empty-state"><Settings size={38}/><h2>Settings</h2><p>Connect this screen to your Spring Boot user preferences API.</p></div>}/>
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing/>}/>
      <Route path="/login" element={<Login/>}/>
      <Route path="/app/*" element={<Shell/>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Routes>
  )
}