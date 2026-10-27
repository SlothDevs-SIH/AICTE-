import { useState } from 'react'
import { api } from '../api'
import { Empty, ErrorBox, Loading, useFetch } from '../components/ui'

const KINDS = [
  ['by_unit', 'Bureau / Cell-wise'], ['by_region', 'Region-wise'], ['by_status', 'Status-wise'],
  ['by_category', 'Category-wise'], ['by_institution', 'Institution-wise'], ['ageing', 'Pending-case ageing'],
  ['disposal_rate', 'Disposal rate'], ['overlaps', 'Overlapping cases'],
]

export default function Reports() {
  const [kind, setKind] = useState('by_unit')
  const r = useFetch<any>(`/reports/${kind}`, [kind])
  const download = async () => {
    const res: Response = await api(`/reports/${kind}?format=csv`, { raw: true })
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${kind}.csv`
    a.click()
    URL.revokeObjectURL(a.href)
  }
  const rows: any[] = r.data?.rows ?? []
  const cols = rows[0] ? Object.keys(rows[0]) : []
  return (
    <>
      <h1>Reports</h1>
      <div className="row" style={{ marginBottom: '1rem' }}>
        <label className="f">Report
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <button className="btn" onClick={download} style={{ alignSelf: 'end' }}>Download CSV</button>
      </div>
      {r.data && <p className="muted">{r.data.caption} · Generated from synthetic data.</p>}
      {r.error && <ErrorBox error={r.error} retry={r.reload} />}
      {r.loading && !r.data && <Loading what="report" />}
      {r.data && rows.length === 0 && <Empty>No rows for this report.</Empty>}
      {rows.length > 0 && (
        <div className="tablewrap">
          <table>
            <thead><tr>{cols.map((c) => <th key={c}>{c.replace(/_/g, ' ')}</th>)}</tr></thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>{cols.map((c) => <td key={c} className={typeof row[c] === 'number' ? 'num' : ''}>{String(row[c] ?? '—')}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
