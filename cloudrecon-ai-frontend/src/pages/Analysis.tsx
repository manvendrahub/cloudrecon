import { useEffect, useState } from 'react'
import { BrainCircuit, CheckCircle2, Cloud, Database, LoaderCircle, ScanSearch, Sparkles } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { getAnalysis } from '../services/api'

const stages=[['Upload validation','Input image and metadata verified'],['Cloud detection','Generating cloud mask'],['Generative reconstruction','Restoring affected regions'],['Quality assessment','Calculating reconstruction metrics']]

export default function Analysis(){
 const [params]=useSearchParams(); const id=params.get('job'); const navigate=useNavigate(); const [job,setJob]=useState<any>(null)
 const step:number=job?.stage??1
 useEffect(()=>{ if(!id) return; const t=setInterval(async()=>{ try{ const {data}=await getAnalysis(id); setJob(data); if(data.status==='Completed'){clearInterval(t); navigate('/app/results?job='+id)} if(data.status==='Failed') clearInterval(t) }catch{} },1000); return()=>clearInterval(t)},[id])
 return <div>
  <div className="page-heading"><div><div className="section-kicker">AI PIPELINE</div><h1>Reconstruction in progress</h1><p>{job?.filename ?? (id ? 'Loading…' : 'No job selected')} · Job {job?.code ?? ''}</p></div><span className="live-pill"><i/> Live processing</span></div>
  <div className="analysis-grid">
   <section className="panel pipeline-panel"><div className="panel-head"><div><h2>Generative reconstruction pipeline</h2><p>Your image is being processed by the AI service.</p></div><BrainCircuit/></div>
    <div className="pipeline">{stages.map((s,i)=><div className={`pipeline-step ${i<step?'done':''} ${i===step-1?'active':''}`} key={s[0]}><div className="pipeline-icon">{i<step?<CheckCircle2 size={18}/>:i===step-1?<LoaderCircle className="spin" size={18}/>:<span>{i+1}</span>}</div><div><b>{s[0]}</b><small>{i===step-1?'Running now':s[1]}</small></div>{i===step-1&&<span className="running">PROCESSING</span>}</div>)}</div>
   </section>
   <section className="panel preview-panel"><div className="panel-head"><div><h2>Cloud analysis preview</h2><p>Estimated cloud coverage</p></div><Cloud/></div><div className="sat-preview"><div className="sat-grid"/><div className="fake-cloud fc1"/><div className="fake-cloud fc2"/><div className="scan-line"/></div><div className="coverage"><div><b>{job?.status==='Completed' ? job.cloudCoverage+'%' : '…'}</b><span>cloud coverage</span></div><div><b>{job?.status==='Completed' ? (100-job.cloudCoverage).toFixed(1)+'%' : '…'}</b><span>clear area</span></div></div></section>
  </div>
  {job?.status==='Failed' && <div className="info-banner"><span><b>Processing failed.</b> {job.error}</span><Link to="/app/upload">Try another image →</Link></div>}
  <div className="info-banner"><Sparkles/><span><b>Connected to the Spring Boot service.</b> You will be taken to the result when processing finishes.</span><span/></div>
 </div>
}