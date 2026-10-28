import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { DotBackdrop } from '../components/DotBackdrop'
import { LoginForm } from '../components/LoginForm'
import { Count, Logo } from '../components/ui'
import { Expandable, ExpandableCard, ExpandableCardContent, ExpandableCardHeader, ExpandableContent, ExpandableTrigger } from '@/components/ui/expandable'
import { ExpandableScreen, ExpandableScreenContent, ExpandableScreenTrigger } from '@/components/ui/expandable-screen'
import { OrganicButton } from '@/components/ui/organic-button'
import { ShiftCard } from '@/components/ui/shift-card'
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

const STEPS: { t: string; sum: string; more: string[]; h: number; c: number }[] = [
  {
    t: 'Unified institution register',
    sum: 'Each complaint is resolved to one verified AICTE institution record, so the Bureau, the PGRC and regional offices work from the same college and the same history.',
    more: [
      'Matching starts from the AICTE ID, then the normalised name with district and state. Spelling variants, abbreviations and renamed colleges resolve to one record.',
      'Look-alike names in the same city are held for an officer to confirm and are never merged automatically.',
      'Every merge, link and correction is attributed to a named officer and written to the audit log.',
    ],
    h: 703, c: 319,
  },
  {
    t: 'Cross-unit overlap detection',
    sum: 'Open cases on the same institution are compared across units. Every alert carries a Match Receipt that shows exactly which rules fired.',
    more: [
      'Four layers are scored and shown separately: institution identity, name similarity, issue similarity and conflict rules.',
      'Issue similarity reads English, Hinglish and Devanagari text through a concept list. An optional model reading is added only when enabled and is labelled as AI-written.',
      'Alerts are capped per officer per day, so priority cases are not buried.',
    ],
    h: 660, c: 296,
  },
  {
    t: 'Action Gate before every step',
    sum: 'Before a notice, closure or transfer is issued, the officer sees what other units have pending against the same institution.',
    more: [
      'The officer can request coordination, link the cases, or proceed with a written justification.',
      'Pairs of actions that contradict each other are classified as Conflict and need a recorded reason to proceed.',
      'Each decision is chained into a tamper-evident audit trail that an auditor can verify.',
    ],
    h: 595, c: 273,
  },
]

const COVERS: { t: string; art: string; d: string }[] = [
  { t: 'Single-window dashboard', art: 'dash', d: 'Received, pending, under process, disposed, transferred, escalated and beyond-timeline cases, with institution-wise and unit-wise views.' },
  { t: 'Case tracking', art: 'track', d: 'Unique case ID, category, status, current unit and officer, last action, next action and expected disposal date.' },
  { t: 'Overlap detection', art: 'overlap', d: 'Rule-based matching on institution identity and name variants, with a plain-language receipt for every flag.' },
  { t: 'Workflow history', art: 'flow', d: 'Every transfer, escalation and remark with who, when and why, kept in a tamper-evident audit chain.' },
  { t: 'Search and filters', art: 'search', d: 'By college, AICTE ID, case ID, unit, region, category, status and date. Filters live in the page address, so a view can be shared.' },
  { t: 'Reports', art: 'report', d: 'Unit-wise, region-wise, status-wise and institution-wise reports, ageing, disposal rate and the overlap list, with CSV export.' },
]

const EVIDENCE: { n: number; of: number; title: string; note: string }[] = [
  { n: 8, of: 8, title: 'Conflicting actions caught', note: 'Planted pairs of contradictory actions, all flagged as Conflict.' },
  { n: 10, of: 10, title: 'Look-alike colleges kept apart', note: 'Colleges with a similar name in the same city; none was wrongly merged.' },
  { n: 13, of: 20, title: 'Misspelled names linked', note: 'Linked automatically. The other 7 go to an officer to confirm, by design.' },
]

function Art({ k }: { k: string }) {
  const b = '#1a3fa8', o = '#ff8a2a', l = '#c9d6f5'
  const frame = (children: React.ReactNode) => (
    <svg viewBox="0 0 120 90" width="132" height="99" aria-hidden="true" className="mx-auto">{children}</svg>
  )
  switch (k) {
    case 'dash': return frame(<><rect x="10" y="10" width="100" height="70" rx="8" fill="#fff" stroke={l} /><rect x="20" y="48" width="12" height="22" rx="3" fill={b} /><rect x="38" y="38" width="12" height="32" rx="3" fill={o} /><rect x="56" y="28" width="12" height="42" rx="3" fill={b} /><circle cx="90" cy="38" r="12" fill="none" stroke={l} strokeWidth="6" /><path d="M90 26a12 12 0 0 1 12 12" fill="none" stroke={o} strokeWidth="6" strokeLinecap="round" /></>)
    case 'track': return frame(<><path d="M24 20v50" stroke={l} strokeWidth="4" strokeLinecap="round" /><circle cx="24" cy="22" r="7" fill={b} /><circle cx="24" cy="45" r="7" fill={o} /><circle cx="24" cy="68" r="7" fill={l} /><rect x="40" y="17" width="60" height="9" rx="4" fill={l} /><rect x="40" y="40" width="46" height="9" rx="4" fill={l} /><rect x="40" y="63" width="54" height="9" rx="4" fill={l} /></>)
    case 'overlap': return frame(<><circle cx="45" cy="45" r="28" fill={b} opacity=".85" /><circle cx="75" cy="45" r="28" fill={o} opacity=".8" /><path d="M60 22a28 28 0 0 1 0 46 28 28 0 0 1 0-46z" fill="#fff" opacity=".9" /></>)
    case 'flow': return frame(<><rect x="8" y="32" width="28" height="26" rx="7" fill={b} /><rect x="46" y="32" width="28" height="26" rx="7" fill={o} /><rect x="84" y="32" width="28" height="26" rx="7" fill={b} /><path d="M36 45h10M74 45h10" stroke={b} strokeWidth="3" strokeLinecap="round" /><path d="M22 64v10h76V64" fill="none" stroke={l} strokeWidth="3" strokeLinecap="round" /></>)
    case 'search': return frame(<><rect x="12" y="14" width="76" height="14" rx="7" fill={l} /><rect x="12" y="36" width="60" height="14" rx="7" fill={l} /><rect x="12" y="58" width="68" height="14" rx="7" fill={l} /><circle cx="86" cy="48" r="17" fill="#fff" stroke={b} strokeWidth="6" /><path d="m99 61 12 12" stroke={o} strokeWidth="7" strokeLinecap="round" /></>)
    default: return frame(<><rect x="12" y="10" width="80" height="70" rx="8" fill="#fff" stroke={l} /><rect x="22" y="52" width="10" height="18" rx="2" fill={b} /><rect x="38" y="42" width="10" height="28" rx="2" fill={b} /><rect x="54" y="32" width="10" height="38" rx="2" fill={o} /><rect x="70" y="22" width="10" height="48" rx="2" fill={b} /><path d="M96 20v52M96 72h14" stroke={l} strokeWidth="3" strokeLinecap="round" fill="none" /></>)
  }
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
            <p className="how-lead">Three safeguards sit between an incoming complaint and an officer's decision. Select a step to see how it works.</p>
            <div className="how-grid">
              {STEPS.map((s, i) => (
                <Expandable key={s.t} expandDirection="vertical" expandBehavior="push" onExpandStart={() => undefined} onCollapseStart={() => undefined}>
                  <ExpandableCard className="w-full relative" collapsedSize={{ width: 320, height: s.c }} expandedSize={{ width: 320, height: s.h }}>
                    <ExpandableTrigger>
                      <ExpandableCardHeader className="p-2">
                        <div>
                          <span className="how-n">{i + 1}</span>
                          <h3 className="how-t">{s.t}</h3>
                        </div>
                        <span className="how-plus" aria-hidden="true">+</span>
                      </ExpandableCardHeader>
                      <ExpandableCardContent className="px-2 pb-2">
                        <p className="how-sum">{s.sum}</p>
                      </ExpandableCardContent>
                    </ExpandableTrigger>
                    <ExpandableContent preset="blur-md" stagger>
                      <ul className="how-more">{s.more.map((m) => <li key={m}>{m}</li>)}</ul>
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
            {COVERS.map((c) => (
              <ShiftCard key={c.t} className="bg-card"
                topContent={
                  <div className="bg-accent text-primary rounded-md shadow-[0px_1px_1px_0px_rgba(0,0,0,0.05),0px_0px_0px_1px_rgba(26,63,168,0.12)_inset]">
                    <h3 className="flex items-center gap-2 p-3 text-base font-semibold"><span className="sc-dot" aria-hidden="true" />{c.t}</h3>
                  </div>
                }
                topAnimateContent={
                  <motion.div className="pointer-events-none absolute -inset-1 rounded-lg border-2 border-dashed border-primary/60"
                    initial={{ opacity: 0, scale: 1.08, filter: 'blur(4px)' }} animate={{ opacity: 1, scale: 1, filter: 'blur(0px)', transition: { delay: 0.2, duration: 0.2 } }} exit={{ opacity: 0, transition: { duration: 0 } }} />
                }
                middleContent={
                  <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="pt-3 text-center">
                    <Art k={c.art} />
                    <span className="mt-3 block text-xs font-medium text-muted-foreground">Hover for detail</span>
                  </motion.div>
                }
                bottomContent={
                  <div className="bg-primary flex h-[194px] w-full flex-col items-center rounded-t-xs border-t border-t-black/10 px-4 text-center">
                    <div className="flex h-[32px] shrink-0 items-center justify-center gap-2 text-[14px] font-semibold text-white"><span className="sc-dot" aria-hidden="true" />{c.t}</div>
                    <p className="flex flex-1 items-center justify-center pb-8 text-[13px] leading-5 text-pretty text-white/85">{c.d}</p>
                  </div>
                } />
            ))}
          </div>
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
                <TextAnimate as="h2" animation="blurInUp" by="word">Sign in to SAMANVAY</TextAnimate>
                <ul className="xs-points">
                  <li><span aria-hidden="true">✓</span>One place for complaints that reach the Bureau, the Cell and regional offices separately.</li>
                  <li><span aria-hidden="true">⇄</span>A warning when another unit already handles the same college, with the evidence shown.</li>
                  <li><span aria-hidden="true">☑</span>An officer always decides. The system only suggests.</li>
                </ul>
                {live && <div className="xs-stats"><div><b><Count to={live.complaints} /></b><span>simulated cases</span></div><div><b><Count to={live.colleges} /></b><span>colleges</span></div><div><b><Count to={live.open_overlaps} /></b><span>open overlaps</span></div></div>}
              </div>
              <div className="xs-right"><LoginForm /></div>
            </div>
          </div>
        </ExpandableScreenContent>
      </div>
    </ExpandableScreen>
  )
}
