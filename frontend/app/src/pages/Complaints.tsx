import { Link, useSearchParams } from 'react-router-dom'
import { qs } from '../api'
import { Empty, ErrorBox, Loading, Severity, StatePill, fmtDate, useFetch } from '../components/ui'

const KEYS = ['q', 'case_id', 'aicte_id', 'unit', 'region', 'category', 'state', 'received_from', 'received_to', 'overdue', 'escalated', 'has_overlap', 'due_soon', 'institution_id', 'older_than_days']

export default function Complaints() {
  const [sp, setSp] = useSearchParams()
  const ref = useFetch<any>('/reference')
  const params = Object.fromEntries(KEYS.map((k) => [k, sp.get(k) ?? '']))
  const offset = Number(sp.get('offset') ?? 0)
  const list = useFetch<any>('/complaints' + qs({ ...params, limit: 25, offset }))
  const set = (k: string, v: string) => {
    const n = new URLSearchParams(sp)
    if (v) n.set(k, v); else n.delete(k)
    n.delete('offset')
    setSp(n, { replace: true })
  }
  const tri = (k: string) => (
    <select value={params[k]} onChange={(e) => set(k, e.target.value)}>
      <option value="">Any</option><option value="true">Yes</option><option value="false">No</option>
    </select>
  )
  const total = list.data?.total ?? 0
  const activeFilters = KEYS.filter((k) => params[k])
  return (
    <>
      <h1>Complaints</h1>
      <div className="card" style={{ marginBottom: '1rem' }}>
        <form className="grid2" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
          <label className="f">Search<input value={params.q} onChange={(e) => set('q', e.target.value)} placeholder="Institution name or title" /></label>
          <label className="f">Case ID / reference no<input value={params.case_id} onChange={(e) => set('case_id', e.target.value)} /></label>
          <label className="f">AICTE permanent ID<input value={params.aicte_id} onChange={(e) => set('aicte_id', e.target.value)} /></label>
          <label className="f">Bureau / Cell
            <select value={params.unit} onChange={(e) => set('unit', e.target.value)}><option value="">Any</option>{ref.data?.units.map((u: any) => <option key={u.id} value={u.code}>{u.code}</option>)}</select></label>
          <label className="f">Region
            <select value={params.region} onChange={(e) => set('region', e.target.value)}><option value="">Any</option>{ref.data?.regions.map((u: any) => <option key={u.id} value={u.code}>{u.name}</option>)}</select></label>
          <label className="f">Category
            <select value={params.category} onChange={(e) => set('category', e.target.value)}><option value="">Any</option>{ref.data?.categories.map((u: any) => <option key={u.id} value={u.code}>{u.name}</option>)}</select></label>
          <label className="f">Status
            <select value={params.state} onChange={(e) => set('state', e.target.value)}><option value="">Any</option>{ref.data?.states.map((s: string) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}</select></label>
          <label className="f">Received from<input type="date" value={params.received_from} onChange={(e) => set('received_from', e.target.value)} /></label>
          <label className="f">Received to<input type="date" value={params.received_to} onChange={(e) => set('received_to', e.target.value)} /></label>
          <label className="f">Older than (days)<input type="number" min={1} value={params.older_than_days} onChange={(e) => set('older_than_days', e.target.value)} /></label>
          <label className="f">Beyond timeline{tri('overdue')}</label>
          <label className="f">Escalated{tri('escalated')}</label>
          <label className="f">Has overlap{tri('has_overlap')}</label>
        </form>
        {activeFilters.length > 0 && <p style={{ margin: '.8rem 0 0' }}><button className="btn sm" onClick={() => setSp({}, { replace: true })}>Clear all filters</button></p>}
      </div>

      {list.error && <ErrorBox error={list.error} retry={list.reload} />}
      {list.loading && !list.data && <Loading what="cases" />}
      {list.data && list.data.items.length === 0 && <Empty>No cases match these filters.</Empty>}
      {list.data && list.data.items.length > 0 && (
        <>
          <p className="muted" role="status">{total} case{total === 1 ? '' : 's'} · showing {offset + 1}–{Math.min(offset + 25, total)}</p>
          <div className="tablewrap">
            <table>
              <caption className="sr">Complaint cases</caption>
              <thead><tr><th>Case ID</th><th>Institution</th><th>Category</th><th>Unit</th><th>Status</th><th>Owner</th><th>Last action</th><th>Next action</th><th>Received</th><th>Expected disposal</th><th>Overlap</th></tr></thead>
              <tbody>
                {list.data.items.map((c: any) => (
                  <tr key={c.id}>
                    <td><Link to={`/app/complaints/${c.id}`}>{c.case_id}</Link><div className="muted">{c.reference_no}</div></td>
                    <td>{c.institution_id ? <Link to={`/app/colleges/${c.institution_id}`}>{c.institution}</Link> : <span title="Not matched to a registry record yet">{c.institution} <span className="badge b-warn">unmatched</span></span>}</td>
                    <td>{c.category}</td><td>{c.unit}</td>
                    <td><StatePill state={c.state} level={c.escalation_level} /> {c.overdue && <span className="badge b-danger">Overdue</span>}</td>
                    <td>{c.owner ?? '—'}</td>
                    <td>{c.last_action_text ?? '—'}</td><td>{c.next_action_text ?? '—'}</td>
                    <td>{fmtDate(c.received_on)}</td><td>{fmtDate(c.expected_disposal_on)}</td>
                    <td><Severity s={c.overlap_severity} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row" style={{ marginTop: '.8rem' }}>
            <button className="btn sm" disabled={offset === 0} onClick={() => { const n = new URLSearchParams(sp); n.set('offset', String(Math.max(0, offset - 25))); setSp(n) }}>← Previous</button>
            <button className="btn sm" disabled={offset + 25 >= total} onClick={() => { const n = new URLSearchParams(sp); n.set('offset', String(offset + 25)); setSp(n) }}>Next →</button>
            <a className="btn sm" href={'#'} onClick={(e) => { e.preventDefault(); window.print() }}>Print view</a>
          </div>
        </>
      )}
    </>
  )
}
