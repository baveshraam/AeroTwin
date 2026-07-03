import { Copilot, AuditChain } from '../panels'

export default function CopilotAudit() {
  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Agentic Intelligence · Traceability</div>
        <h1>MRO Copilot &amp; Audit Trail</h1>
        <p>Ask the twin in plain language — the agent calls real tools and never invents a limit. Every airworthiness decision it helps produce is written to a tamper-evident, hash-chained record built for regulatory audit.</p>
      </div>

      <div className="card">
        <h2>MRO Copilot <span className="tt">agentic · offline · citation-gated</span></h2>
        <Copilot />
      </div>

      <div className="card">
        <h2>Tamper-evident audit trail <span className="tt">SHA-256 hash chain</span></h2>
        <AuditChain />
      </div>
    </div>
  )
}
