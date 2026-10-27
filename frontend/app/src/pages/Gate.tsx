import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, ApiError, qs } from '../api'
import { Severity, useFetch } from '../components/ui'

const ACTIONS = [
  ['ISSUE_NOTICE', 'Issue notice'], ['IMPOSE_PENALTY', 'Impose penalty'],
  ['CLOSE_CASE', 'Close case'], ['WITHDRAW_APPROVAL', 'Withdraw approval'],
]
const CHOICE_LABEL: Record<string, string> = {
  REQUEST_COORDINATION: 'Request coordination (puts this case on hold)',
  LINK: 'Link the cases',
  PROCEED: 'Proceed anyway',
}

export default function Gate() {
  const [sp] = useSearchParams()
  const [complaintId, setComplaintId] = useState(sp.get('complaint_id') ?? '')
  const [institutionId, setInstitutionId] = useState('')
  const [q, setQ] = useState('')
  const [action, setAction] = useState('ISSUE_NOTICE')
  const [res, setRes] = useState<any>(null)
  const [err, setErr] = useState<ApiError | null>(null)
  const [choice, setChoice] = useState('')
  const [just, setJust] = useState('')
  const [done, setDone] = useState<any>(null)
  const inst = useFetch<any>(q.length > 1 ? `/institutions${qs({ q, limit: 8 })}` : null, [q])
  const run = async () => {
    setErr(null); setRes(null); setDone(null); setChoice('')
    try {
      setRes(await api('/gate/check', {
        method: 'POST',
        body: { complaint_id: complaintId || undefined, institution_id: institutionId || undefined, action_type: action },
      }))
    } catch (e) {
      setErr(e as ApiError)
    }
  }
  const decide = async () => {
    setErr(null)
    try {
      setDone(await api(`/gate/${res.check_id}/decision`, { method: 'POST', body: { choice, justification: just || undefined } }))
    } catch (e) {
      setErr(e as ApiError)
    }
  }
  return (
    <>
      <h1>Action Gate</h1>
      <p className="muted" style={{ maxWidth: '44rem' }}>
        Before you take a regulatory action, check what other units are doing at the same college. The check and your decision are recorded.
      </p>
      <div className="card grid2">
        <label className="f">Action you are about to take
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            {ACTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        {complaintId ? (
          <p>Case selected. <button className="btn sm" onClick={() => setComplaintId('')}>Use a college instead</button></p>
        ) : (
          <div>
            <label className="f">Search college
              <input value={q} onChange={(e) => { setQ(e.target.value); setInstitutionId('') }} placeholder="Type a college name or AICTE ID" />
            </label>
            {inst.data?.items.map((i: any) => (
              <label key={i.id} style={{ display: 'flex', gap: '.5rem', alignItems: 'center', padding: '.2rem 0' }}>
                <input type="radio" name="gi" style={{ width: 'auto', minHeight: 0 }} checked={institutionId === i.id} onChange={() => setInstitutionId(i.id)} /> {i.name}
              </label>
            ))}
          </div>
        )}
        <div><button className="btn primary" disabled={!complaintId && !institutionId} onClick={run}>Check before acting</button></div>
      </div>
      {err && <div className="notice err" role="alert" style={{ marginTop: '1rem' }}>{err.message}</div>}
      {res && (
        <section className="card" style={{ marginTop: '1rem' }} aria-live="polite">
          <h2>Result: <Severity s={res.result} /></h2>
          {res.result === 'CLEAR' && <p>No other unit has an open case on this college. You can proceed.</p>}
          {res.other_cases.length > 0 && (
            <div className="tablewrap">
              <table>
                <thead><tr><th>Case</th><th>State</th><th>Last action</th><th>Why shown</th></tr></thead>
                <tbody>
                  {res.other_cases.map((c: any) => (
                    <tr key={c.id}>
                      <td><Link to={`/app/complaints/${c.id}`}>{c.case_id}</Link></td>
                      <td>{c.state.replace('_', ' ').toLowerCase()}</td>
                      <td>{c.last_action_text ?? '—'}</td>
                      <td>{c.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {!done ? (
            <>
              <fieldset style={{ border: 0, padding: 0, marginTop: '1rem' }}>
                <legend><strong>Your decision</strong></legend>
                {res.choices.map((c: string) => (
                  <label key={c} style={{ display: 'flex', gap: '.5rem', alignItems: 'center', padding: '.2rem 0' }}>
                    <input type="radio" name="ch" style={{ width: 'auto', minHeight: 0 }} checked={choice === c} onChange={() => setChoice(c)} />
                    {CHOICE_LABEL[c]}
                  </label>
                ))}
              </fieldset>
              <label className="f">
                Justification {res.result === 'CONFLICT' && choice === 'PROCEED' ? '(required, at least 15 characters)' : '(optional)'}
                <textarea value={just} onChange={(e) => setJust(e.target.value)} />
              </label>
              <p><button className="btn primary" disabled={!choice} onClick={decide}>Record decision</button></p>
            </>
          ) : (
            <div className="notice ok" role="status">
              Decision recorded: {done.choice.replace('_', ' ').toLowerCase()}. It is part of the audit trail.
            </div>
          )}
        </section>
      )}
    </>
  )
}
