import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { LockKeyhole, Mail, Satellite, ShieldCheck } from 'lucide-react'
import { login } from '../services/api'

export default function Login() {
  const [email,setEmail]=useState('researcher@cloudrecon.ai')
  const [password,setPassword]=useState('demo123')
  const navigate=useNavigate()
  const [error,setError]=useState('')

  const submit=async(e:FormEvent)=>{e.preventDefault(); setError(''); try{const {data}=await login(email,password); localStorage.setItem('cloudrecon_token',data.token); navigate('/app')}catch{setError('Wrong email or password, or the server is not running.')}}
  return <div className="auth-page">
    <div className="auth-visual"><div className="auth-orb"/><div className="auth-copy"><div className="brand"><div className="brand-mark"><Satellite/></div><strong>CloudRecon AI</strong></div><h1>Turn obscured imagery into usable insight.</h1><p>A professional workspace for cloud detection, AI reconstruction and satellite-image quality assessment.</p></div></div>
    <div className="auth-panel">
      <Link className="back-link" to="/">← Back to home</Link>
      <div className="auth-form"><div className="auth-icon"><ShieldCheck/></div><div className="section-kicker">SECURE WORKSPACE</div><h2>Welcome back</h2><p>Sign in to continue your satellite analysis.</p>
        <form onSubmit={submit}>
          <label>Email<input value={email} onChange={e=>setEmail(e.target.value)} type="email" required/><Mail/></label>
          <label>Password<input value={password} onChange={e=>setPassword(e.target.value)} type="password" required/><LockKeyhole/></label>
          <button className="btn btn-primary full">Sign in to workspace</button>
        </form>
        {error && <small className="demo-note">{error}</small>}
      </div>
    </div>
  </div>
}