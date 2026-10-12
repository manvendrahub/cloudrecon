import { ArrowRight, CheckCircle2, CloudOff, Eye, Layers3, Satellite, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div className="landing">
      <header className="landing-nav">
        <div className="brand">
          <div className="brand-mark"><Satellite size={21}/></div>
          <div><strong>CloudRecon</strong><span>AI SATELLITE LAB</span></div>
        </div>
        <div className="landing-links">
          <a href="#technology">Technology</a><a href="#workflow">Workflow</a><a href="#about">About</a>
          <Link className="btn btn-outline" to="/login">Sign in</Link>
        </div>
      </header>

      <section className="hero">
        <div className="hero-grid"/>
        <div className="hero-copy">
          <div className="eyebrow"><Sparkles size={15}/> GENERATIVE AI FOR EARTH OBSERVATION</div>
          <h1>See beyond the clouds with <em>AI reconstruction.</em></h1>
          <p>CloudRecon restores cloud-obscured LISS-IV satellite imagery using an AI-assisted reconstruction pipeline, helping researchers explore clearer land-surface information.</p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/login">Open workspace <ArrowRight size={17}/></Link>
            <a className="btn btn-ghost" href="#technology">Explore technology</a>
          </div>
          <div className="trust-row"><CheckCircle2 size={16}/> Research-ready workflow <span/> <CheckCircle2 size={16}/> GeoTIFF-aware pipeline <span/> <CheckCircle2 size={16}/> Java API ready</div>
        </div>
        <div className="hero-orbit">
          <div className="orbit orbit-a"/><div className="orbit orbit-b"/>
          <div className="earth">
            <div className="continent c1"/><div className="continent c2"/><div className="continent c3"/>
            <div className="cloud cloud-a"/><div className="cloud cloud-b"/>
          </div>
          <div className="orbit-tag tag-a">LISS-IV</div><div className="orbit-tag tag-b">AI MODEL</div>
        </div>
      </section>

      <section className="feature-strip" id="technology">
        <div><CloudOff/><b>Cloud detection</b><span>Identify cloud-obscured regions.</span></div>
        <div><Layers3/><b>Generative reconstruction</b><span>Rebuild missing visual information.</span></div>
        <div><Eye/><b>Quality assessment</b><span>Compare and validate outputs.</span></div>
      </section>

      <section className="workflow-section" id="workflow">
        <div className="section-kicker">FROM IMAGE TO INSIGHT</div>
        <h2>A focused satellite-imagery workflow.</h2>
        <div className="workflow">
          {['Upload LISS-IV imagery','Detect clouds & generate mask','Run generative reconstruction','Review, compare & export'].map((x,i)=>(
            <div className="workflow-card" key={x}><span>0{i+1}</span><h3>{x}</h3><p>{['Upload imagery into a controlled processing workspace.','Estimate cloud coverage and isolate affected pixels.','Send the prepared input to your AI reconstruction service.','Inspect metrics and download the reconstructed output.'][i]}</p></div>
          ))}
        </div>
      </section>

      <footer id="about"><div className="brand"><div className="brand-mark"><Satellite size={18}/></div><strong>CloudRecon AI</strong></div><span>Generative cloud removal & reconstruction for LISS-IV imagery.</span></footer>
    </div>
  )
}