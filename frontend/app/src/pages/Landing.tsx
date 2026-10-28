import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { DotBackdrop } from '../components/DotBackdrop'
import { AuthPanel } from '../components/AuthPanel'
import { Count, Logo } from '../components/ui'
import { ExpandableScreen, ExpandableScreenContent, ExpandableScreenTrigger } from '@/components/ui/expandable-screen'
import { News } from '@/components/ui/sidebar-news'
import { CoverPopup } from '../components/CoverPopup'
import { StepWidget } from '../components/StepWidget'
import { OrganicButton } from '@/components/ui/organic-button'
import { TextAnimate } from '@/components/ui/text-animate'

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

const STEPS: { t: string; sum: string; more: string[] }[] = [
  {
    t: 'Unified institution register',
    sum: 'Each complaint is resolved to one verified AICTE institution record, so the Bureau, the PGRC and regional offices work from the same college and the same history.',
    more: [
      'Matching starts from the AICTE ID, then the normalised name with district and state. Spelling variants, abbreviations and renamed colleges resolve to one record.',
      'Look-alike names in the same city are held for an officer to confirm and are never merged automatically.',
      'Every merge, link and correction is attributed to a named officer and written to the audit log.',
    ],
  },
  {
    t: 'Cross-unit overlap detection',
    sum: 'Open cases on the same institution are compared across units. Every alert carries a Match Receipt that shows exactly which rules fired.',
    more: [
      'Four layers are scored and shown separately: institution identity, name similarity, issue similarity and conflict rules.',
      'Issue similarity reads English, Hinglish and Devanagari text through a concept list. An optional model reading is added only when enabled and is labelled as AI-written.',
      'Alerts are capped per officer per day, so priority cases are not buried.',
    ],
  },
  {
    t: 'Action Gate before every step',
    sum: 'Before a notice, closure or transfer is issued, the officer sees what other units have pending against the same institution.',
    more: [
      'The officer can request coordination, link the cases, or proceed with a written justification.',
      'Pairs of actions that contradict each other are classified as Conflict and need a recorded reason to proceed.',
      'Each decision is chained into a tamper-evident audit trail that an auditor can verify.',
    ],
  },
]

const COVERS: { t: string; tag: string; img: string; d: string; more: string[] }[] = [
  { t: 'Single-window dashboard', tag: 'Overview', img: 'dash', d: 'Every case, by status, unit and institution, on one screen.', more: [
    'Counts for received, pending, under process, disposed, transferred, escalated and beyond-timeline cases, updated live.',
    'Institution-wise and unit-wise views, with cases due within seven days called out.',
    'Role-aware: an officer sees their own unit, management and the Competent Authority see everything.'] },
  { t: 'Case tracking', tag: 'Tracking', img: 'track', d: 'One record per case, from receipt to disposal.', more: [
    'A unique case ID and the reference number from the source, with category, status, current unit and officer.',
    'Last action, next action and expected disposal date in one place, checked against the category time limit.',
    'Every transfer, escalation and remark is attached to the case with who, when and why.'] },
  { t: 'Overlap detection', tag: 'Detection', img: 'overlap', d: 'Warns when two units hold open cases on the same college.', more: [
    'Matches on the AICTE ID first, then on name variants, issue wording and conflicting actions.',
    'Every flag comes with a Match Receipt: which layers fired, the score, and the reasons in plain language.',
    'Officers confirm, dismiss or link. Nothing is merged, linked or closed automatically.'] },
  { t: 'Workflow history', tag: 'Audit', img: 'flow', d: 'A tamper-evident record of every action taken.', more: [
    'Each audit entry carries the hash of the one before it, so edits, deletions and reordering show up.',
    'An auditor can re-compute the whole chain with one click and see the head hash.',
    'Entries name the person, the action and the record, so responsibility is never unclear.'] },
  { t: 'Search and filters', tag: 'Search', img: 'search', d: 'Find a case by college, ID, unit, status or date.', more: [
    'Filters for college, AICTE ID, case ID, unit, region, category, status, date range, overdue, escalated and overlap.',
    'College search tolerates spelling variants and word order.',
    'Filters live in the page address, so a filtered view can be shared as a link.'] },
  { t: 'Reports', tag: 'Reporting', img: 'report', d: 'Unit, region, status and institution reports with export.', more: [
    'Unit-wise, region-wise, status-wise and institution-wise reports, with ageing and disposal rate.',
    'The overlap list and a one-page brief for any overlap, ready to print.',
    'CSV export for every report.'] },
]

const EVIDENCE: { n: number; of: number; title: string; note: string }[] = [
  { n: 8, of: 8, title: 'Conflicting actions caught', note: 'Planted pairs of contradictory actions, all flagged as Conflict.' },
  { n: 10, of: 10, title: 'Look-alike colleges kept apart', note: 'Colleges with a similar name in the same city; none was wrongly merged.' },
  { n: 13, of: 20, title: 'Misspelled names linked', note: 'Linked automatically. The other 7 go to an officer to confirm, by design.' },
]

/** The SAMANVAY mark drawing itself, shown when every card has been swiped away. */
function MarkDraw() {
  return (
    <svg viewBox="0 0 32 32" width="72" height="72" fill="none" aria-hidden="true" className="text-primary">
      <path d="M9 21c0-6 5-9 9-9h5M23 12l-3-3m3 3-3 3M9 21h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" strokeDasharray="60">
        <animate attributeName="stroke-dashoffset" dur="2500ms" values="60;0;0;0;60" fill="freeze" />
      </path>
    </svg>
  )
}

function Ring({ pct }: { pct: number }) {
  return (
    <svg viewBox="0 0 120 120" width="124" height="124" aria-hidden="true" className="evi-ring">
      <circle cx="60" cy="60" r="50" fill="none" stroke="var(--surface-2)" strokeWidth="12" />
      <motion.circle cx="60" cy="60" r="50" fill="none" stroke="#1a3fa8" strokeWidth="12" strokeLinecap="round" transform="rotate(-90 60 60)"
        initial={{ pathLength: 0 }} whileInView={{ pathLength: pct }} viewport={{ once: true }} transition={{ duration: 1.4, ease: 'easeOut' }} />
      <defs><linearGradient id="evg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#1a3fa8" /><stop offset="1" stopColor="#ff8a2a" /></linearGradient></defs>
    </svg>
  )
}

export default function Landing() {
  const { me } = useAuth()
  const nav = useNavigate()
  const [live, setLive] = useState<any>(null)
  const [open, setOpen] = useState<(typeof COVERS)[number] | null>(null)
  const [allGone, setAllGone] = useState(false)
  const [round, setRound] = useState(0)
  useEffect(() => () => { document.body.style.overflow = '' }, []) // the sign-in panel locks scrolling; leaving the page must release it
  useEffect(() => {
    fetch('/api/v1/public/overview').then((r) => (r.ok ? r.json() : null)).then(setLive).catch(() => setLive(null))
  }, [])
  return (
    <ExpandableScreen layoutId="cta-card" triggerRadius="100px" contentRadius="24px">
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
            <TextAnimate as="p" animation="blurInUp" by="line" delay={0.5} className="lead">
              AICTE complaints reach the Regulation Bureau, the Public Grievance Redressal Cell and regional offices separately. SAMANVAY puts them in one place, warns an officer when another unit is already handling the same college, and shows exactly why.
            </TextAnimate>
            {me ? (
              <OrganicButton href="/app" size="lg" label="Open the dashboard" onClick={(e) => { e.preventDefault(); nav('/app') }} />
            ) : (
              <ExpandableScreenTrigger>
                <OrganicButton href="#get-started" size="lg" label="Get started" onClick={(e) => e.preventDefault()} />
              </ExpandableScreenTrigger>
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
        </section>

        <section className="section" id="how">
          <TextAnimate as="h2" animation="blurInUp" by="word" once>How it works</TextAnimate>
          <div className="how-box">
            <p className="how-lead">Three safeguards sit between an incoming complaint and an officer's decision. Tap a step to open it.</p>
            <div className="how-grid">
              {STEPS.map((st, i) => <StepWidget key={st.t} n={i + 1} title={st.t} summary={st.sum} points={st.more} />)}
            </div>
          </div>
        </section>

        <section className="section" id="covers" style={{ paddingTop: 0 }}>
          <TextAnimate as="h2" animation="blurInUp" by="word" once>What it covers</TextAnimate>
          <div className="cover-wrap">
            <div className="cover-copy">
              <p className="lead">Six screens make up the dashboard. The cards are stacked: <strong>swipe</strong> the top one away to see the next, or <strong>click</strong> it to read what that part does.</p>
              <ul className="cover-hints">
                <li><span aria-hidden="true">↔</span> Swipe left or right to dismiss</li>
                <li><span aria-hidden="true">◉</span> Click to open the details</li>
              </ul>
              {allGone && <button type="button" className="btn primary" onClick={() => { setAllGone(false); setRound((r) => r + 1) }}>Show the cards again</button>}
            </div>
            <div className="cover-deck">
              {!allGone && (
                <News key={round} zoom articles={COVERS.map((c) => ({ href: c.img, title: c.t, summary: c.d, image: `/shots/${c.img}.jpg` }))}
                  onOpen={(a) => setOpen(COVERS.find((c) => c.img === a.href) ?? null)} onEmpty={() => setAllGone(true)} emptyLogo={<MarkDraw />} />
              )}
            </div>
          </div>
          <CoverPopup open={!!open} onClose={() => setOpen(null)} title={open?.t ?? ''} subtitle={open?.tag ?? ''}
            media={open && (
              <div className="grid h-full w-full place-items-center bg-linear-to-br from-[#12306f] via-primary to-[#2459d6] p-5">
                <div className="w-full overflow-hidden rounded-xl bg-white shadow-2xl ring-1 ring-white/30" style={{ aspectRatio: '0.72' }}>
                  <img src={`/shots/${open.img}.jpg`} alt={`${open.t}, a screen of the running prototype`} className="block max-w-none" style={{ width: '230%', marginLeft: '-43%' }} />
                </div>
              </div>
            )}>
            {open && (
              <div className="flex flex-col gap-5">
                <p className="text-base leading-relaxed text-foreground">{open.d}</p>
                {open.more.map((m, j) => (
                  <div key={m} className="flex items-start gap-3">
                    <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-primary text-xs font-bold text-primary-foreground">{j + 1}</span>
                    <p className="text-muted-foreground">{m}</p>
                  </div>
                ))}
                <p className="border-t border-border pt-3 text-xs text-muted-foreground">Screen from the running prototype, showing simulated data.</p>
              </div>
            )}
          </CoverPopup>
        </section>

        <section className="section" id="evidence" style={{ paddingTop: 0 }}>
          <TextAnimate as="h2" animation="blurInUp" by="word" once>What we have measured, and what we have not</TextAnimate>
          <p className="muted" style={{ maxWidth: '46rem' }}>
            AICTE does not publish complaint records, so the complaints in this prototype are simulated; the college registry can be loaded with real AICTE
            approved institutions. The results below come from planted test scenarios that we created ourselves, so they show that the rules work as designed.
            They are not a promise about real AICTE data.
          </p>
          <div className="evi-grid">
            {EVIDENCE.map((e) => (
              <div className="evi" key={e.title}>
                <div className="evi-ringwrap">
                  <Ring pct={e.n / e.of} />
                  <div className="evi-num"><b><Count to={e.n} /></b><span>of {e.of}</span></div>
                </div>
                <h3>{e.title}</h3>
                <p>{e.note}</p>
              </div>
            ))}
          </div>
        </section>

        <footer className="lfoot">
          <span>SAMANVAY · Team SlothDevs · Smart India Hackathon · AICTE (Regulation Bureau) problem statement</span>
          <span><Link to="/login">Sign in</Link> · Complaints are simulated</span>
        </footer>

        <ExpandableScreenContent className="xs-content">
          <div className="xs-center">
            <div className="xs-grid">
              <div className="xs-left">
                <TextAnimate as="h2" animation="blurInUp" by="word">Join or sign in to SAMANVAY</TextAnimate>
                <ul className="xs-points">
                  <li><span aria-hidden="true">✓</span>One place for complaints that reach the Bureau, the Cell and regional offices separately.</li>
                  <li><span aria-hidden="true">⇄</span>A warning when another unit already handles the same college, with the evidence shown.</li>
                  <li><span aria-hidden="true">☑</span>An officer always decides. The system only suggests.</li>
                </ul>
                {live && <div className="xs-stats"><div><b><Count to={live.complaints} /></b><span>simulated cases</span></div><div><b><Count to={live.colleges} /></b><span>colleges</span></div><div><b><Count to={live.open_overlaps} /></b><span>open overlaps</span></div></div>}
              </div>
              <div className="xs-right"><AuthPanel /></div>
            </div>
          </div>
        </ExpandableScreenContent>
      </div>
    </ExpandableScreen>
  )
}
