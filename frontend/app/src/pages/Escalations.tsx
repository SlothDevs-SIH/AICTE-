import { Link } from 'react-router-dom'
import { Empty, ErrorBox, Loading, StatePill, fmtDate, useFetch } from '../components/ui'

export default function Escalations() {
  const l = useFetch<any>('/escalations')
  return (
    <>
      <h1>Escalations</h1>
      {l.error && <ErrorBox error={l.error} retry={l.reload} />}
      {l.loading && !l.data && <Loading what="escalations" />}
      {l.data && l.data.items.length === 0 && <Empty>No escalated cases in your scope.</Empty>}
      {l.data && l.data.items.length > 0 && (
        <div className="tablewrap">
          <table>
            <thead><tr><th>Case</th><th>College</th><th>Unit</th><th>Level</th><th>Last action</th><th>Due</th></tr></thead>
            <tbody>
              {l.data.items.map((c: any) => (
                <tr key={c.id}>
                  <td><Link to={`/app/complaints/${c.id}`}>{c.case_id}</Link></td>
                  <td>{c.institution}</td><td>{c.unit}</td>
                  <td><StatePill state="ESCALATED" level={c.escalation_level} /></td>
                  <td>{c.last_action_text}</td><td>{fmtDate(c.due_on)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
