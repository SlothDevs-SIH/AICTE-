import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import { ExpandableScreen, ExpandableScreenContent, ExpandableScreenTrigger } from '../components/ExpandableScreen'
import { ShiftCard } from '../components/ShiftCard'
import { DotBackdrop } from '../components/DotPattern'
import { InteractiveHoverButton } from '../components/InteractiveHoverButton'
import { TextAnimate } from '../components/TextAnimate'
import { Expandable, ExpandableCard, ExpandableCardContent, ExpandableCardHeader, ExpandableContent, ExpandableTrigger } from '../components/Expandable'
import { LoginForm } from '../components/LoginForm'
import { Count, Logo } from '../components/ui'

function SkylineArt() {
  // Abstract campus-and-city illustration drawn in SVG (no photos, so nothing is borrowed).
  const blocks = [[60, 330, 70, 150], [150, 290, 60, 190], [225, 340, 80, 140], [330, 250, 70, 230], [415, 310, 90, 170], [525, 270, 60, 210], [600, 335, 85, 145], [705, 240, 70, 240], [795, 300, 80, 180], [890, 260, 65, 220], [970, 330, 90, 150], [1075, 280, 70, 200]]
  return (
    <svg viewBox="0 0 1200 480" preserveAspectRatio="xMidYMax slice" width="100%" height="100%" aria-hidden="true">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#dbe6fb" /><stop offset="1" stopColor="#f2f5fc" /></linearGradient>
        <linearGradient id="b1" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#7f9fe0" /><stop offset="1" stopColor="#bcd0f2" /></linearGradient>
        <linearGradient id="b2" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#3f66c4" /><stop offset="1" stopColor="#9bb6ea" /></linearGradient>
      </defs>
      <rect width="1200" height="480" fill="url(#sky)" />
      <circle cx="930" cy="110" r="58" fill="#ff9a4a" opacity=".7" />
      {blocks.map(([x, y, w, h], i) => (
        <g key={i}>
          <rect x={x} y={y} width={w} height={h} fill={i % 2 ? 'url(#b1)' : 'url(#b2)'} />
          {Array.from({ length: Math.floor(h / 34) }).map((_, r) => (
            <g key={r}>
              <rect x={x + 10} y={y + 14 + r * 34} width="12" height="14" fill="#f2f5fc" opacity=".7" />
              <rect x={x + w - 24} y={y + 14 + r * 34} width="12" height="14" fill="#f2f5fc" opacity=".7" />
            </g>
          ))}
        </g>
      ))}
      <path d="M0 470 Q300 430 600 455 T1200 440 V480 H0Z" fill="#1a3fa8" opacity=".85" />
      <circle cx="590" cy="318" r="14" fill="#ff9a4a" stroke="#1a3fa8" strokeWidth="3" />
      <path d="M590 318 L520 430" stroke="#1a3fa8" strokeWidth="2" strokeDasharray="4 5" />
    </svg>
  )
}

export default function Landing() {
  const { me } = useAuth()
  const [live, setLive] = useState<any>(null)
  useEffect(() => {
    fetch('/api/v1/public/overview').then((r) => (r.ok ? r.json() : null)).then(setLive).catch(() => setLive(null))
  }, [])
  return (
    <div className="land">
      <DotBackdrop />
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
          <h1 id="h"><TextAnimate as="span" animation="blurInUp" by="word">Coordinate</TextAnimate> <mark className="hl"><TextAnimate as="span" animation="blurInUp" by="word" delay={0.2}>before</TextAnimate></mark> <TextAnimate as="span" animation="blurInUp" by="word" delay={0.35}>you act.</TextAnimate></h1>
          <TextAnimate as="p" animation="blurInUp" by="word" delay={0.5} duration={1.2} className="lead">AICTE complaints reach the Regulation Bureau, the Public Grievance Redressal Cell and regional offices separately. SAMANVAY puts them in one place, warns an officer when another unit is already handling the same college, and shows exactly why.</TextAnimate>
          {me ? <InteractiveHoverButton to="/app" className="ihb-lg">Open the dashboard</InteractiveHoverButton> : (
            <ExpandableScreen layoutId="cta-card" triggerRadius="100px" contentRadius="24px">
              <ExpandableScreenTrigger>
                <InteractiveHoverButton as="span" className="ihb-lg">Get started</InteractiveHoverButton>
              </ExpandableScreenTrigger>
              <ExpandableScreenContent className="xs-content">
                <div className="xs-grid">
                  <div className="xs-left">
                    <h2>Sign in to SAMANVAY</h2>
                    <ul className="xs-points">
                      <li><span aria-hidden="true">✓</span>One place for complaints that reach the Bureau, the Cell and regional offices separately.</li>
                      <li><span aria-hidden="true">⇄</span>A warning when another unit already handles the same college, with the evidence shown.</li>
                      <li><span aria-hidden="true">☑</span>An officer always decides. The system only suggests.</li>
                    </ul>
                    {live && <div className="xs-stats"><div><b><Count to={live.complaints} /></b><span>simulated cases</span></div><div><b><Count to={live.colleges} /></b><span>colleges</span></div><div><b><Count to={live.open_overlaps} /></b><span>open overlaps</span></div></div>}
                  </div>
                  <div className="xs-right"><LoginForm /></div>
                </div>
              </ExpandableScreenContent>
            </ExpandableScreen>
          )}
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
        <TextAnimate as="h2" animation="blurInUp" by="word" once>How it works</TextAnimate>
        <div className="how-box">
          <p className="how-lead">Three safeguards sit between an incoming complaint and an officer's decision. Select a step to see what it does.</p>
          <div className="how-grid">
            {[
              ['One verified record per institution', 'Every complaint, from every Bureau and Cell, resolves to a single AICTE institution record.', [
                'Spelling variants, abbreviations and renamed colleges are matched on name, district and AICTE ID.',
                'Look-alike colleges in one city are never merged automatically; uncertain matches go to an officer to confirm.',
                'Each link records who confirmed it, when, and why.']],
              ['Early warning, with the evidence', 'When two units hold open cases on the same college, the officer sees why before acting.', [
                'A Match Receipt lists every rule that fired: same college, same issue, conflicting actions.',
                'The same problem described in different words (English, Hinglish, Devanagari) is matched by concept, with an optional, clearly labelled AI reading.',
                'No alert without an explanation, and each officer has a daily alert limit.']],
              ['A gate before every action', 'Notices, closures and transfers pass an Action Gate that shows what the other unit is doing.', [
                'The officer can request coordination, link the cases, or proceed with a written reason.',
                'Conflicting actions on one college are flagged for a second look; the system only suggests, a person decides.',
                'Every decision is written to a tamper-evident audit chain.']],
            ].map(([t, sum, more], i) => (
              <Expandable key={t as string} expandDirection="vertical" expandBehavior="push">
                <ExpandableCard collapsedSize={{ width: 310, height: 215 }} expandedSize={{ width: 310, height: undefined }}>
                  <ExpandableTrigger>
                    <ExpandableCardHeader>
                      <div><span className="how-n">{i + 1}</span><h3>{t as string}</h3></div>
                      <span className="how-plus" aria-hidden="true">+</span>
                    </ExpandableCardHeader>
                    <ExpandableCardContent><p>{sum as string}</p></ExpandableCardContent>
                  </ExpandableTrigger>
                  <ExpandableContent preset="blur-md" stagger>
                    <ul className="how-more">{(more as string[]).map((m) => <li key={m}>{m}</li>)}</ul>
                  </ExpandableContent>
                </ExpandableCard>
              </Expandable>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="covers" style={{ paddingTop: 0 }}>
        <TextAnimate as="h2" animation="blurInUp" by="word" once>What it covers</TextAnimate>
        <div className="sc-grid">
          {[
            ['Single-window dashboard', '▦', 'Received, pending, under process, disposed, transferred, escalated and beyond-timeline cases, with institution-wise and unit-wise views.'],
            ['Case tracking', '☰', 'Unique case ID, category, status, current unit and officer, last action, next action, and expected disposal date.'],
            ['Overlap detection', '⇄', 'Rule-based matching on institution identity and name variants, with a plain-language receipt.'],
            ['Workflow history', '◷', 'Every transfer, escalation and remark with who, when and why. Tamper-evident audit chain.'],
            ['Search and filters', '⌕', 'By college, AICTE ID, case ID, unit, region, category, status and date. Filters live in the page address, so a view can be shared.'],
            ['Reports', '▤', 'Unit-wise, region-wise, status-wise and institution-wise reports, ageing, disposal rate, and overlap list, with CSV export.'],
          ].map(([t, ic, d]) => (
            <ShiftCard key={t}
              topContent={<div className="sc-slab"><h3><i aria-hidden="true">{ic}</i>{t}</h3></div>}
              middleContent={<motion.div key="m" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}><span className="sc-big" aria-hidden="true">{ic}</span><span className="sc-hint">Hover or tap for detail</span></motion.div>}
              bottomContent={<><b>{t}</b><p>{d}</p></>} />
          ))}
        </div>
      </section>

      <section className="section" id="evidence" style={{ paddingTop: 0 }}>
        <TextAnimate as="h2" animation="blurInUp" by="word" once>What we have measured, and what we have not</TextAnimate>
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
      </section>

      <footer className="lfoot">
        <span>SAMANVAY · Team SlothDevs · Smart India Hackathon · AICTE (Regulation Bureau) problem statement</span>
        <span><Link to="/login">Sign in</Link> · Complaints are simulated</span>
      </footer>
    </div>
  )
}
