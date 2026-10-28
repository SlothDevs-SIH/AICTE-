import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, qs } from '../api'
import { Severity, useFetch } from '../components/ui'

export default function NewComplaint() {
  const ref = useFetch<any>('/reference')
  const [f, setF] = useState({ reference_no: '', category_id: '', title: '', description: '', institution_text_raw: '', aicte_id_raw: '', institution_id: '', complainant_name: '', complainant_phone: '', complainant_email: '' })
  const [sugg, setSugg] = useState<any[]>([])
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<any>(null)
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }))

  useEffect(() => {
    if (f.institution_text_raw.trim().length < 3 && !f.aicte_id_raw) { setSugg([]); return }
    const t = setTimeout(async () => {
      try { setSugg((await api(`/institutions/suggest${qs({ text: f.institution_text_raw, aicte_id: f.aicte_id_raw })}`)).items) } catch { setSugg([]) }
    }, 300)
    return () => clearTimeout(t)
  }, [f.institution_text_raw, f.aicte_id_raw])

  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const body: any = { ...f }
      Object.keys(body).forEach((k) => body[k] === '' && delete body[k])
      setResult(await api('/complaints', { method: 'POST', body }))
    } catch (x) {
      const a = x as ApiError
      setErr(a.code === 'duplicate_reference' ? 'This unit already has a case with that reference number.' : a.message)
    } finally { setBusy(false) }
  }

  if (result) {
    const c = result.complaint
    return (
      <>
        <h1>Case registered</h1>
        <div className="notice ok" role="status">Case <strong>{c.case_id}</strong> created for <strong>{c.institution}</strong>.</div>
        {result.institution_match.status === 'needs_review' && <div className="notice warn" style={{ marginTop: '1rem' }}>The college name was close to more than one registry record, so it was <strong>not</strong> linked automatically. Open the case and choose the right college.</div>}
        {result.institution_match.status === 'unmatched' && <div className="notice warn" style={{ marginTop: '1rem' }}>No registry record matched. The case is saved with the typed name and no overlap check could run.</div>}
        {c.overlap_severity ? (
          <div className="notice warn" style={{ marginTop: '1rem' }} role="alert">
            <Severity s={c.overlap_severity} /> <strong>Potential Overlapping Cases – Coordination Required.</strong> Another unit has an open case on this college. <Link to="/app/overlaps">Review the suggested overlap</Link>.
          </div>
        ) : <p className="muted">No other unit has an open case on this college.</p>}
        <p className="row"><Link className="btn primary" to={`/app/complaints/${c.id}`}>Open case</Link><button className="btn" onClick={() => { setResult(null); setF({ ...f, reference_no: '', title: '' }) }}>Add another</button></p>
      </>
    )
  }
  return (
    <>
      <h1>New complaint</h1>
      <form className="card grid2" onSubmit={submit}>
        <label className="f">Your unit reference number<input required value={f.reference_no} onChange={(e) => set('reference_no', e.target.value)} placeholder="RB/2026/0300" /></label>
        <label className="f">Category
          <select required value={f.category_id} onChange={(e) => set('category_id', e.target.value)}><option value="">Choose…</option>{ref.data?.categories.map((c: any) => <option key={c.id} value={c.id}>{c.name} (SLA {c.sla_days} days)</option>)}</select></label>
        <label className="f" style={{ gridColumn: '1 / -1' }}>Title<input required minLength={3} value={f.title} onChange={(e) => set('title', e.target.value)} /></label>
        <label className="f" style={{ gridColumn: '1 / -1' }}>Description<textarea value={f.description} onChange={(e) => set('description', e.target.value)} /></label>
        <label className="f">College name as written in the complaint<input value={f.institution_text_raw} onChange={(e) => { set('institution_text_raw', e.target.value); set('institution_id', '') }} /><small>Spelling variants are fine. The registry is searched as you type.</small></label>
        <label className="f">AICTE permanent ID (if given)<input value={f.aicte_id_raw} onChange={(e) => set('aicte_id_raw', e.target.value)} /></label>
        {sugg.length > 0 && (
          <fieldset style={{ gridColumn: '1 / -1', border: '1px solid var(--line)', borderRadius: 10 }}>
            <legend>Possible registry matches</legend>
            {sugg.map((s) => (
              <label key={s.institution_id} style={{ display: 'flex', gap: '.6rem', padding: '.3rem 0', alignItems: 'center' }}>
                <input type="radio" style={{ width: 'auto', minHeight: 0 }} name="inst" checked={f.institution_id === s.institution_id} onChange={() => set('institution_id', s.institution_id)} />
                <span><strong>{s.name}</strong> <span className="muted">match score {s.match_score.toFixed(2)} · {s.evidence.rule}</span></span>
              </label>
            ))}
            <p className="muted" style={{ margin: '.3rem 0 0' }}>If you choose none, the system links the best match only when it is very close; otherwise it asks you later.</p>
          </fieldset>
        )}
        <label className="f">Complainant name<small>Encrypted; shown masked</small><input value={f.complainant_name} onChange={(e) => set('complainant_name', e.target.value)} /></label>
        <label className="f">Complainant phone<input value={f.complainant_phone} onChange={(e) => set('complainant_phone', e.target.value)} /></label>
        <label className="f">Complainant email<input type="email" value={f.complainant_email} onChange={(e) => set('complainant_email', e.target.value)} /></label>
        {err && <div className="notice err" role="alert" style={{ gridColumn: '1 / -1' }}>{err}</div>}
        <div style={{ gridColumn: '1 / -1' }}><button className="btn primary" disabled={busy}>{busy ? 'Saving…' : 'Register case'}</button></div>
      </form>
    </>
  )
}
