import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Count, Logo } from '../components/ui'

function SkylineArt() {
  // Abstract campus-and-city illustration drawn in SVG (no photos, so nothing is borrowed).
  const blocks = [[60, 330, 70, 150], [150, 290, 60, 190], [225, 340, 80, 140], [330, 250, 70, 230], [415, 310, 90, 170], [525, 270, 60, 210], [600, 335, 85, 145], [705, 240, 70, 240], [795, 300, 80, 180], [890, 260, 65, 220], [970, 330, 90, 150], [1075, 280, 70, 200]]
  return (
    <svg viewBox="0 0 1200 480" preserveAspectRatio="xMidYMax slice" width="100%" height="100%" aria-hidden="true">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#dfe9d3" /><stop offset="1" stopColor="#f2f3e6" /></linearGradient>
        <linearGradient id="b1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7fa88d" /><stop offset="1" stopColor="#bcd3c2" /></linearGradient>
        <linearGradient id="b2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#4c7d63" /><stop offset="1" stopColor="#9bbfa8" /></linearGradient>
      </defs>
      <rect width="1200" height="480" fill="url(#sky)" />
      <circle cx="930" cy="110" r="58" fill="#d6f36b" opacity=".7" />
      {blocks.map(([x, y, w, h], i) => (
        <g key={i}>
          <rect x={x} y={y} width={w} height={h} fill={i % 2 ? 'url(#b1)' : 'url(#b2)'} />
          {Array.from({ length: Math.floor(h / 34) }).map((_, r) => (
            <g key={r}>
              <rect x={x + 10} y={y + 14 + r * 34} width="12" height="14" fill="#f7f7f0" opacity=".7" />
              <rect x={x + w - 24} y={y + 14 + r * 34} width="12" height="14" fill="#f7f7f0" opacity=".7" />
            </g>
          ))}
        </g>
      ))}
      <path d="M0 470 Q300 430 600 455 T1200 440 V480 H0Z" fill="#1f4d3a" opacity=".85" />
      <circle cx="590" cy="318" r="14" fill="#d6f36b" stroke="#1f4d3a" strokeWidth="3" />
      <path d="M590 318 L520 430" stroke="#1f4d3a" strokeWidth="2" strokeDasharray="4 5" />
    </svg>
  )
}

export default function Landing() {
  const [live, setLive] = useState<any>(null)
  useEffect(() => {
    fetch('/api/v1/public/overview').then((r) => (r.ok ? r.json() : null)).then(setLive).catch(() => setLive(null))
  }, [])
  return (
    <div className="land">
      <header className="lnav">
        <Link to="/" className="brand"><Logo /> SAMANVAY</Link>
        <nav aria-label="Sections">
          <a href="#how">How it works</a>
          <a href="#covers">What it covers</a>
          <a href="#evidence">Evidence</a>
          <Link to="/login">Dashboard</Link>
        </nav>
      </header>

      <section className="hero" aria-labelledby="h">
        <div className="hero-art"><SkylineArt /></div>
        <div className="hero-copy">
          <h1 id="h">Coordinate <mark className="hl">before</mark> you act.</h1>
          <p className="lead">
            AICTE complaints reach the Regulation Bureau, the Public Grievance Redressal Cell and regional offices separately.
            SAMANVAY puts them in one place, warns an officer when another unit is already handling the same college, and shows
            exactly why.
          </p>
          <Link className="cta" to="/login">Open the dashboard <span aria-hidden="true">→</span></Link>
          <p className="small">An officer always decides. The system only suggests, and every suggestion comes with its evidence.</p>
        </div>

        <div className="floatcard" aria-live="polite">
          {live ? (
            <>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <strong>Potential Overlapping Cases – Coordination Required</strong>
                <span className="badge b-danger">Conflict</span>
              </div>
              {live.sample_conflict ? (
                <>
                  <p style={{ margin: '.5rem 0 .2rem' }}><strong>{live.sample_conflict.institution}</strong></p>
                  <p className="muted" style={{ margin: 0 }}>Open with {live.sample_conflict.units.join(' and ')}</p>
                  <p className="muted" style={{ margin: '.6rem 0 0', fontSize: '.85rem' }}>Why: {live.sample_conflict.reasons.join(' · ').toLowerCase()}.</p>
                </>
              ) : <p className="muted">No conflict is open right now.</p>}
              <div className="livestats">
                <div><span className="n"><Count to={live.complaints} /></span><span className="l">cases tracked</span></div>
                <div><span className="n"><Count to={live.colleges} /></span><span className="l">colleges in the registry</span></div>
                <div><span className="n"><Count to={live.open_overlaps} /></span><span className="l">open overlaps</span></div>
              </div>
            </>
          ) : <p className="muted">Reading the running system…</p>}
        </div>
        <div className="pill">
          {live ? `Live from this running system. ${live.complaints_simulated === live.complaints ? 'Cases are simulated' : 'Some cases are simulated'}; ${live.colleges_real > 0 ? `${live.colleges_real.toLocaleString('en-IN')} colleges are real AICTE records` : 'the college list is not yet real AICTE data'}.` : 'Reading the running system…'}
        </div>
      </section>

      <section className="section" id="how">
        <h2>How it works</h2>
        <div className="steps">
          <div className="step"><h3>One record per college</h3><p className="muted">Every case, from every Bureau or Cell, is linked to a single institution record. Spelling variants of a college name resolve to the same record; look-alike names in the same city do not.</p></div>
          <div className="step"><h3>A warning with its reasons</h3><p className="muted">When two units hold open cases on one college, the officer sees a Match Receipt: which rules fired and what each case says. No alert without an explanation.</p></div>
          <div className="step"><h3>A gate before action</h3><p className="muted">Before issuing a notice or closing a case, the Action Gate shows what the other unit is doing. The officer can request coordination, link the cases, or proceed with a written reason. All recorded.</p></div>
        </div>
      </section>

      <section className="section" id="covers" style={{ paddingTop: 0 }}>
        <h2>What it covers</h2>
        <div className="feat">
          {[
            ['Single-window dashboard', 'Received, pending, under process, disposed, transferred, escalated and beyond-timeline cases, with institution-wise and unit-wise views.'],
            ['Case tracking', 'Unique case ID, category, status, current unit and officer, last action, next action, and expected disposal date.'],
            ['Overlap detection', 'Rule-based matching on institution identity and name variants, with a plain-language receipt.'],
            ['Workflow history', 'Every transfer, escalation and remark with who, when and why. Tamper-evident audit chain.'],
            ['Search and filters', 'By college, AICTE ID, case ID, unit, region, category, status and date. Filters live in the page address, so a view can be shared.'],
            ['Reports', 'Unit-wise, region-wise, status-wise and institution-wise reports, ageing, disposal rate, and overlap list, with CSV export.'],
          ].map(([t, d]) => (
            <div className="card" key={t}><h3>{t}</h3><p className="muted" style={{ margin: 0 }}>{d}</p></div>
          ))}
        </div>
      </section>

      <section className="section" id="evidence" style={{ paddingTop: 0 }}>
        <h2>What we have measured, and what we have not</h2>
        <p className="muted" style={{ maxWidth: '46rem' }}>
          AICTE does not publish complaint records, so the complaints in this prototype are simulated; the college registry can be loaded with real AICTE
          approved institutions. The numbers below come from planted test scenarios that we created ourselves, so they show the rules work as designed.
          They are not a promise about real AICTE data.
        </p>
        <div className="feat">
          <div className="card"><div className="stat">8 of 8</div><p className="muted" style={{ margin: 0 }}>planted conflicting-action pairs flagged as Conflict.</p></div>
          <div className="card"><div className="stat">0 of 10</div><p className="muted" style={{ margin: 0 }}>look-alike colleges wrongly merged with a similar name in the same city.</p></div>
          <div className="card"><div className="stat">13 of 20</div><p className="muted" style={{ margin: 0 }}>misspelled names linked automatically. The other 7 are sent to an officer to confirm, by design.</p></div>
        </div>
        <p className="muted" style={{ maxWidth: '46rem' }}><strong>Built:</strong> matching of different wording for the same issue through a hand-written concept list (English, Hinglish, Devanagari), coordination threads, bulk import and PDF briefs. <strong>Not built:</strong> a neural language model for matching, and Hindi-script college-name matching.</p>
      </section>

      <footer className="lfoot">
        <span>SAMANVAY · Team SlothDevs · Smart India Hackathon · AICTE (Regulation Bureau) problem statement</span>
        <span><Link to="/login">Sign in</Link> · Complaints are simulated</span>
      </footer>
    </div>
  )
}
