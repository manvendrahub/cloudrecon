import { useEffect, useState, type CSSProperties } from 'react'
import { Download, FileText, Printer, RefreshCcw, Sparkles } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { downloadUrl, getResult, imageUrl, startAnalysis } from '../services/api'

const engineName=(e:string)=>({'generative-ai':'Generative AI (LaMa)','reference-fill':'Reference image fill','opencv-inpaint':'OpenCV inpainting (basic fallback)','java-diffusion':'Java fill (basic fallback)'} as Record<string,string>)[e]??e

export default function Results(){
 const [params]=useSearchParams(); const id=params.get('job'); const navigate=useNavigate()
 const [job,setJob]=useState<any>(null); const [split,setSplit]=useState(50); const [view,setView]=useState<'output'|'mask'>('output')
 useEffect(()=>{ if(id) getResult(id).then(r=>setJob(r.data)).catch(()=>{}) },[id])
 const report=(()=>{ try{ return job?.report?JSON.parse(job.report):null }catch{ return null } })()
 const saveReport=()=>{
  if(!report) return
  const li=(a:string[])=>a.map(x=>`<li>${x}</li>`).join('')
  const lc=report.landCover
  const html=`<!doctype html><meta charset="utf-8"><title>${report.title}</title><style>body{font:16px/1.6 system-ui;max-width:780px;margin:2rem auto;padding:0 1rem;color:#12202f}h1{font-size:1.6rem}h2{margin-top:1.6rem;font-size:1.15rem}td,th{padding:6px 14px;border-bottom:1px solid #ddd;text-align:left}small{color:#667}</style><h1>${report.title}</h1><small>Generated ${report.generatedAt}</small><h2>Summary</h2><p>${report.summary}</p><h2>Data quality</h2><p>${report.quality.label}. Cloud cover ${report.quality.cloudCoverage}%, confidence ${report.quality.confidence}%, engine ${report.quality.engine}.</p><h2>Land cover (after reconstruction)</h2><table><tr><th>Vegetation</th><th>Water / dark</th><th>Bare / built-up</th><th>Cloud (reconstructed)</th></tr><tr><td>${lc.vegetation}%</td><td>${lc.water}%</td><td>${lc.bareBuilt}%</td><td>${lc.cloud}%</td></tr></table><h2>Observations</h2><ul>${li(report.observations)}</ul><h2>Recommendations</h2><ul>${li(report.recommendations)}</ul><h2>Limitations</h2><ul>${li(report.limitations)}</ul>`
  const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([html],{type:'text/html'})); a.download=(job.code||'report')+'-situation-report.html'; a.click()
 }
 if(!id) return <div className="empty-state"><h2>No result selected</h2><p>Open a job from your history, or <Link to="/app/upload">upload an image</Link>.</p></div>
 if(!job) return <div className="empty-state"><h2>Loading result…</h2></div>
 const fill:CSSProperties={position:'absolute',inset:0,width:'100%',height:'100%',objectFit:'contain'}
 const reprocess=async()=>{ await startAnalysis(id); navigate('/app/analysis?job='+id) }
 return <div>
  <div className="page-heading"><div><div className="section-kicker">RECONSTRUCTION RESULT</div><h1>{job.filename}</h1><p>{job.status} · {job.date} · {engineName(job.engine)}</p></div><div className="heading-actions"><button className="btn btn-ghost" onClick={()=>setView(v=>v==='output'?'mask':'output')}>{view==='output'?'Show cloud mask':'Show reconstruction'}</button><a className="btn btn-primary" href={downloadUrl(id)}><Download size={16}/> Export result</a></div></div>
  <div className="result-grid">
   <section className="panel compare-panel"><div className="compare-toolbar"><span>Before / after comparison</span></div>
    <div className="comparison" style={{position:'relative',display:'block',minHeight:380}}>
     <img src={imageUrl(id,view)} alt="Result" style={fill}/>
     <img src={imageUrl(id,'input')} alt="Original" style={{...fill,clipPath:`inset(0 ${100-split}% 0 0)`}}/>
     <div style={{position:'absolute',top:0,bottom:0,left:split+'%',width:3,background:'#fff',pointerEvents:'none'}}/>
     <input type="range" min={0} max={100} value={split} onChange={e=>setSplit(+e.target.value)} aria-label="Compare original and result" style={{position:'absolute',inset:0,width:'100%',height:'100%',opacity:0,cursor:'ew-resize'}}/>
    </div>
    <div className="compare-caption"><span>Left: original · Right: {view==='output'?'reconstructed':'cloud mask'}. Drag to compare.</span><b>{job.cloudRemoval}% of detected cloud removed</b></div>
   </section>
   <aside className="result-side">
    <div className="panel quality-card"><div className="section-kicker">QUALITY SCORE</div><div className="big-score">{job.reconstructionScore}<span>/100</span></div><p>Heuristic score from cloud removal and the amount of surrounding clear area. Validate against ground truth before operational use.</p><div className="quality-row"><span>Cloud coverage</span><b>{job.cloudCoverage}%</b></div><div className="quality-row"><span>Cloud removal</span><b>{job.cloudRemoval}%</b></div><div className="quality-row"><span>Confidence</span><b>{job.confidence}%</b></div><div className="quality-row"><span>Processing time</span><b>{job.duration}</b></div></div>
    <div className="panel model-card"><Sparkles/><div><b>Engine</b><span>{engineName(job.engine)}</span></div><button onClick={reprocess}><RefreshCcw size={15}/> Reprocess</button></div>
   </aside>
  </div>
  {report ? <section className="panel" style={{marginTop:24,padding:24}}>
   <div style={{display:'flex',justifyContent:'space-between',flexWrap:'wrap',gap:12}}><div><div className="section-kicker">SITUATION REPORT</div><h2 style={{margin:'4px 0 0'}}>{report.title}</h2><small>Generated {report.generatedAt}</small></div><div style={{display:'flex',gap:8}}><button className="btn btn-ghost" onClick={saveReport}><FileText size={16}/> Download report</button><button className="btn btn-ghost" onClick={()=>window.print()}><Printer size={16}/> Print</button></div></div>
   <p style={{marginTop:16}}>{report.summary}</p>
   <div className="stats" style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(150px,1fr))',gap:12,margin:'16px 0'}}>
    {([['Vegetation',report.landCover.vegetation],['Water / dark',report.landCover.water],['Bare / built-up',report.landCover.bareBuilt],['Cloud rebuilt',report.landCover.cloud]] as [string,number][]).map(([k,v])=><div key={k} style={{borderLeft:'3px solid #38b6c8',paddingLeft:10}}><div style={{opacity:.7,fontSize:13}}>{k}</div><b style={{fontSize:22}}>{v}%</b></div>)}
   </div>
   <h3>Observations</h3><ul>{report.observations.map((o:string,i:number)=><li key={i}>{o}</li>)}</ul>
   <h3>Recommendations</h3><ul>{report.recommendations.map((o:string,i:number)=><li key={i}>{o}</li>)}</ul>
   <h3>Limitations</h3><ul style={{opacity:.75}}>{report.limitations.map((o:string,i:number)=><li key={i}>{o}</li>)}</ul>
  </section> : <p className="demo-note" style={{marginTop:24}}>No situation report: the Python AI service was not running, so the weaker Java engine was used. Start the AI service and reprocess this image.</p>}
  <div className="result-footer"><Link to="/app/upload">Process another image</Link><span>{job.width} × {job.height} px</span></div>
 </div>
}
