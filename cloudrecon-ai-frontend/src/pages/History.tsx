import { useEffect, useState } from 'react'
import { Download, FileImage, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { downloadUrl, getHistory } from '../services/api'

export default function History(){
 const [rows,setRows]=useState<any[]>([]); const [q,setQ]=useState('')
 useEffect(()=>{ getHistory().then(r=>setRows(r.data)).catch(()=>{}) },[])
 const shown=rows.filter(r=>(r.filename+r.code).toLowerCase().includes(q.toLowerCase()))
 return <div><div className="page-heading"><div><div className="section-kicker">WORKSPACE</div><h1>Processing history</h1><p>Review previous cloud-removal and reconstruction jobs.</p></div></div>
  <section className="panel table-panel"><div className="history-tools"><div className="search-box"><Search size={16}/><input placeholder="Search image or job ID" value={q} onChange={e=>setQ(e.target.value)}/></div></div>
  <div className="table-wrap"><table><thead><tr><th>JOB</th><th>IMAGE</th><th>DATE</th><th>STATUS</th><th>QUALITY</th><th>OUTPUT</th></tr></thead><tbody>
   {shown.map(r=><tr key={r.id}><td><b>{r.code}</b></td><td><FileImage size={16}/>{r.status==='Completed'?<Link to={'/app/results?job='+r.id}>{r.filename}</Link>:r.filename}</td><td>{r.date}</td><td><span className={`status ${r.status.toLowerCase()}`}>{r.status}</span></td><td>{r.status==='Completed'?r.reconstructionScore+'%':'—'}</td><td>{r.status==='Completed'&&<a className="download-mini" href={downloadUrl(r.id)}><Download size={15}/></a>}</td></tr>)}
   {shown.length===0&&<tr><td colSpan={6}>No jobs yet. Upload an image to start.</td></tr>}
  </tbody></table></div></section></div>
}
