import { useEffect, useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { api, ApiError } from '../api'
import { ROLE_LABEL, useAuth } from '../auth'
import { DotBackdrop } from '../components/DotBackdrop'
import { useDebounced, useFetch } from '../components/ui'
import { OrganicButton } from '@/components/ui/organic-button'
import { TextAnimate } from '@/components/ui/text-animate'

const STAFF_CHOICES = ['unit_officer', 'unit_supervisor', 'regional_officer', 'management', 'competent_authority', 'auditor']
const STAFF_HELP: Record<string, string> = {
  unit_officer: 'Handles cases in a Bureau or Cell', unit_supervisor: 'Supervises a Bureau or Cell',
  regional_officer: 'Works in a regional office', management: 'Reviews trends and performance',
  competent_authority: 'Takes final decisions', auditor: 'Verifies the record',
}

type Kind = 'complainant' | 'institution' | 'staff'
const CARDS: { kind: Kind; title: string; text: string; tag: string; instant: boolean; art: ReactNode }[] = [
  {
    kind: 'complainant', title: 'I want to file or follow a complaint', instant: true, tag: 'Instant access',
    text: 'For students, parents, faculty and members of the public. File a complaint about an institution and follow its progress.',
    art: <svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="22" r="11" fill="#1a3fa8" /><path d="M10 56c2-13 11-20 22-20s20 7 22 20z" fill="#1a3fa8" /><circle cx="48" cy="16" r="9" fill="#ff8a2a" /><path d="M44 16h8M48 12v8" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" /></svg>,
  },
  {
    kind: 'institution', title: 'I represent an institution', instant: false, tag: 'Needs approval',
    text: 'See how many complaints about your college are open or closed, and their stage. An administrator confirms you first.',
    art: <svg viewBox="0 0 64 64" aria-hidden="true"><path d="M8 26 32 12l24 14z" fill="#1a3fa8" /><rect x="12" y="28" width="6" height="22" fill="#ff8a2a" /><rect x="24" y="28" width="6" height="22" fill="#ff8a2a" /><rect x="34" y="28" width="6" height="22" fill="#ff8a2a" /><rect x="46" y="28" width="6" height="22" fill="#ff8a2a" /><rect x="8" y="52" width="48" height="6" rx="2" fill="#1a3fa8" /></svg>,
  },
  {
    kind: 'staff', title: 'I work at AICTE', instant: false, tag: 'Needs approval',
    text: 'For officers, supervisors, regional offices, management and auditors. An administrator checks your role before you can open case files.',
    art: <svg viewBox="0 0 64 64" aria-hidden="true"><rect x="10" y="14" width="44" height="36" rx="6" fill="#1a3fa8" /><rect x="16" y="22" width="14" height="4" rx="2" fill="#fff" /><rect x="16" y="30" width="24" height="4" rx="2" fill="#c9d6f5" /><rect x="16" y="38" width="18" height="4" rx="2" fill="#c9d6f5" /><circle cx="46" cy="40" r="10" fill="#ff8a2a" /><path d="m41 40 4 4 7-8" stroke="#fff" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>,
  },
]

function InstitutionPicker({ onPick }: { onPick: (i: any) => void }) {
  const [q, setQ] = useState('')
  const dq = useDebounced(q.trim(), 300)
  const res = useFetch<any>(dq.length >= 2 ? `/institutions?q=${encodeURIComponent(dq)}&limit=8` : null, [dq])
  return (
    <div>
      <label className="f">Search for your institution
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name, city or AICTE ID" autoFocus />
      </label>
      {dq.length >= 2 && res.data && (
        <ul className="pick-list">
          {res.data.items.length === 0 && <li className="muted">No institution matches. Try fewer words.</li>}
          {res.data.items.map((i: any) => (
            <li key={i.id}><button type="button" onClick={() => onPick(i)}><strong>{i.name}</strong><span>{[i.district, i.state].filter(Boolean).join(', ')}{i.aicte_id ? ` · ${i.aicte_id}` : ''}</span></button></li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function ChooseRole() {
  const { me, reloadMe, logout } = useAuth()
  const ref = useFetch<any>('/reference')
  const [kind, setKind] = useState<Kind | null>(null)
  const [inst, setInst] = useState<any>(null)
  const [role, setRole] = useState('')
  const [unit, setUnit] = useState('')
  const [region, setRegion] = useState('')
  const [note, setNote] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const first = (me?.name ?? '').split(' ')[0]
  const rejected = me?.request?.status === 'rejected' ? me.request : null

  const needUnit = role === 'unit_officer' || role === 'unit_supervisor'
  const needRegion = role === 'regional_officer'
  const ready = kind === 'complainant' || (kind === 'institution' && inst) || (kind === 'staff' && role && (!needUnit || unit) && (!needRegion || region))

  const submit = async () => {
    setBusy(true); setErr('')
    try {
      const body = kind === 'complainant' ? { account_type: 'complainant' }
        : kind === 'institution' ? { account_type: 'institution', institution_id: inst.id, note }
        : { account_type: 'staff', role, unit_code: needUnit ? unit : null, region_code: needRegion ? region : null, note }
      await api('/me/role', { method: 'POST', body })
      await reloadMe()
    } catch (e) { setErr((e as ApiError).message) } finally { setBusy(false) }
  }

  return (
    <div className="pick-wrap">
      <DotBackdrop />
      <button type="button" className="btn sm pick-out" onClick={logout}>Sign out</button>
      <div className="pick-in">
        <TextAnimate as="h1" animation="blurInUp" by="word">{`Welcome${first ? ', ' + first : ''}. Who are you?`}</TextAnimate>
        <p className="muted pick-lead">Your e-mail is verified. Tell us how you will use SAMANVAY so we can show you the right screens. You can ask an administrator to change this later.</p>
        {rejected && <div className="notice err" role="alert"><strong>Your last request was not approved.</strong> {rejected.reason} You can choose again.</div>}
        <div className="pick-grid" role="radiogroup" aria-label="Who are you">
          {CARDS.map((c, i) => (
            <motion.button key={c.kind} type="button" role="radio" aria-checked={kind === c.kind}
              className={`pick-card ${kind === c.kind ? 'on' : ''}`} onClick={() => { setKind(c.kind); setErr('') }}
              initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + i * 0.08, type: 'spring', stiffness: 220, damping: 22 }}
              whileHover={{ y: -6 }} whileTap={{ scale: 0.98 }}>
              <span className="pick-art">{c.art}</span>
              <strong>{c.title}</strong>
              <span className="pick-text">{c.text}</span>
              <span className={`badge ${c.instant ? 'b-ok' : 'b-warn'}`}>{c.tag}</span>
            </motion.button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {kind && (
            <motion.div key={kind} className="card pick-more" initial={{ opacity: 0, y: 16, filter: 'blur(6px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} exit={{ opacity: 0, y: 8 }}>
              {kind === 'complainant' && <p style={{ margin: 0 }}>You will land on your own page, where you can file a complaint and follow each one. Only you and the officers who handle it see what you write.</p>}
              {kind === 'institution' && (
                <>
                  {inst ? (
                    <p className="pick-chosen"><span><strong>{inst.name}</strong><br /><span className="muted">{[inst.district, inst.state].filter(Boolean).join(', ')}</span></span> <button type="button" className="btn sm" onClick={() => setInst(null)}>Change</button></p>
                  ) : <InstitutionPicker onPick={setInst} />}
                  <label className="f" style={{ marginTop: '.8rem' }}>Your position and anything that helps us confirm it <small>(optional)</small>
                    <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} placeholder="For example: Registrar, official e-mail domain" />
                  </label>
                </>
              )}
              {kind === 'staff' && (
                <>
                  <div className="pick-roles">
                    {STAFF_CHOICES.map((r) => (
                      <button key={r} type="button" className={role === r ? 'on' : ''} aria-pressed={role === r} onClick={() => setRole(r)}><strong>{ROLE_LABEL[r]}</strong><span>{STAFF_HELP[r]}</span></button>
                    ))}
                  </div>
                  {needUnit && (
                    <label className="f" style={{ marginTop: '.8rem' }}>Your Bureau or Cell
                      <select value={unit} onChange={(e) => setUnit(e.target.value)}><option value="">Choose…</option>{ref.data?.units.filter((u: any) => !u.code.startsWith('RO')).map((u: any) => <option key={u.id} value={u.code}>{u.code} · {u.name}</option>)}</select>
                    </label>
                  )}
                  {needRegion && (
                    <label className="f" style={{ marginTop: '.8rem' }}>Your region
                      <select value={region} onChange={(e) => setRegion(e.target.value)}><option value="">Choose…</option>{ref.data?.regions.map((r: any) => <option key={r.id} value={r.code}>{r.name}</option>)}</select>
                    </label>
                  )}
                  <label className="f" style={{ marginTop: '.8rem' }}>Note for the administrator <small>(optional)</small>
                    <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} placeholder="Your designation, employee ID or who can vouch for you" />
                  </label>
                </>
              )}
              {err && <div className="notice err" role="alert" style={{ marginTop: '.8rem' }}>{err}</div>}
              <p style={{ margin: '1rem 0 0' }}>
                <OrganicButton href="#continue" label={busy ? 'Saving…' : kind === 'complainant' ? 'Continue' : 'Send request'} onClick={(e) => { e.preventDefault(); if (ready && !busy) submit() }} className={ready ? '' : 'opacity-50'} />
                {!ready && <span className="muted" style={{ marginLeft: '.8rem' }}>{kind === 'institution' ? 'Choose your institution first.' : 'Choose your role first.'}</span>}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export function Waiting() {
  const { me, reloadMe, logout } = useAuth()
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    const t = setInterval(() => { reloadMe() }, 10000)  // notice an approval without a reload
    return () => clearInterval(t)
  }, [reloadMe])
  const r = me?.request
  const what = r?.type === 'institution' ? `Institution representative, ${r.institution_name}` : `${ROLE_LABEL[r?.role ?? ''] ?? 'Staff'}${r?.unit_code ? ` · ${r.unit_code}` : ''}${r?.region_code ? ` · ${r.region_code}` : ''}`
  return (
    <div className="pick-wrap">
      <DotBackdrop />
      <div className="card pick-wait">
        <div className="auth-mail" aria-hidden="true">⏳</div>
        <h1 style={{ fontSize: '1.7rem' }}>Waiting for approval</h1>
        <p className="muted">An administrator has your request and will review it. This page updates by itself once it is approved. You do not need to stay on it.</p>
        <p className="pick-chosen" style={{ justifyContent: 'center' }}><span><span className="muted">You asked for</span><br /><strong>{what}</strong></span></p>
        <p style={{ display: 'flex', gap: '.6rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button type="button" className="btn" disabled={busy} onClick={async () => { setBusy(true); try { await api('/me/role/cancel', { method: 'POST' }); await reloadMe() } finally { setBusy(false) } }}>Withdraw and choose again</button>
          <button type="button" className="btn" onClick={logout}>Sign out</button>
        </p>
      </div>
    </div>
  )
}
