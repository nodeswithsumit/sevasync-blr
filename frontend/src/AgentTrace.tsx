// ─────────────────────────────────────────────────────────────────────────────
// Column 2 — Live 4-Agent Reasoning Trace
// ─────────────────────────────────────────────────────────────────────────────
import {
  InlineNotification,
  ProgressBar,
  Tag,
  Tile,
} from '@carbon/react'
import {
  CheckmarkFilled,
  ErrorFilled,
  WarningFilled,
} from '@carbon/icons-react'
import type {
  AgentTraceEntry,
  Discrepancy,
  OrchestrateResponse,
} from './types'

interface Props {
  result: OrchestrateResponse | null
}

const AGENT_LABELS: Record<string, string> = {
  'Intake & Policy Router': 'Agent 1 — Intake & Policy Router',
  'Pre-Flight Discrepancy Validator': 'Agent 2 — Pre-Flight Discrepancy Validator',
  'Live Bengaluru Geo & Ward Router': 'Agent 3 — Live Bengaluru Geo & Ward Router',
  'Bilingual Action & Draft Agent': 'Agent 4 — Bilingual Action & Draft Agent',
}

function agentLabel(name: string): string {
  return AGENT_LABELS[name] ?? name
}

function StatusIcon({ status }: { status: AgentTraceEntry['status'] }) {
  const size = 20
  if (status === 'pass')
    return <CheckmarkFilled size={size} style={{ color: 'var(--cds-support-success)' }} />
  if (status === 'warn')
    return <WarningFilled size={size} style={{ color: 'var(--cds-support-warning)' }} />
  return <ErrorFilled size={size} style={{ color: 'var(--cds-support-error)' }} />
}

function AgentCard({ entry }: { entry: AgentTraceEntry }) {
  const borderColor =
    entry.status === 'pass'
      ? 'var(--cds-support-success)'
      : entry.status === 'warn'
        ? 'var(--cds-support-warning)'
        : 'var(--cds-support-error)'

  return (
    <div
      style={{
        borderLeft: `3px solid ${borderColor}`,
        paddingLeft: '0.75rem',
        marginBottom: '0.75rem',
        background: 'var(--cds-layer-01)',
        borderRadius: '0 2px 2px 0',
        padding: '0.75rem 0.75rem 0.75rem 1rem',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          marginBottom: '0.25rem',
        }}
      >
        <StatusIcon status={entry.status} />
        <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>
          {agentLabel(entry.agent_name)}
        </span>
        <Tag type="gray" size="sm">
          {entry.latency_ms} ms
        </Tag>
      </div>
      <p
        style={{
          fontSize: '0.8125rem',
          color: 'var(--cds-text-secondary)',
          marginBottom: entry.findings.length ? '0.5rem' : 0,
        }}
      >
        {entry.summary}
      </p>
      {entry.findings.length > 0 && (
        <ul
          style={{
            margin: 0,
            paddingLeft: '1rem',
            fontSize: '0.8125rem',
            color: 'var(--cds-text-primary)',
          }}
        >
          {entry.findings.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function DiscrepancyItem({ d }: { d: Discrepancy }) {
  const kind = d.severity === 'critical' ? 'error' : 'warning'
  const subtitle = d.remediation
    ? `${d.message} ➜ ${d.remediation}`
    : d.message
  return (
    <InlineNotification
      kind={kind}
      lowContrast
      hideCloseButton
      title={`[${d.code}] ${d.field}`}
      subtitle={subtitle}
      style={{ marginBottom: '0.5rem', maxWidth: '100%' }}
    />
  )
}

export default function AgentTrace({ result }: Props) {
  if (!result) {
    return (
      <Tile style={{ height: '100%' }}>
        <h4
          style={{
            marginBottom: '0.5rem',
            fontWeight: 600,
            fontSize: '1rem',
            color: 'var(--cds-text-primary)',
          }}
        >
          Live 4-Agent Reasoning Trace
        </h4>
        <p style={{ color: 'var(--cds-text-secondary)', fontSize: '0.875rem' }}>
          Run the Pre-Flight Audit to see the agent pipeline results here.
        </p>
      </Tile>
    )
  }

  const { readiness_score, status, live_geo_check, agent_trace, discrepancies, selected_policy } =
    result

  const statusKind: 'green' | 'red' =
    status === 'READY_TO_SUBMIT' ? 'green' : 'red'

  return (
    <Tile style={{ height: '100%' }}>
      <h4
        style={{
          marginBottom: '1rem',
          fontWeight: 600,
          fontSize: '1rem',
          color: 'var(--cds-text-primary)',
        }}
      >
        Live 4-Agent Reasoning Trace
      </h4>

      {/* ── Policy Chip ─────────────────────────────────────────────────── */}
      <p style={{ fontSize: '0.8125rem', marginBottom: '0.5rem', color: 'var(--cds-text-secondary)' }}>
        Policy:{' '}
        <strong>
          {selected_policy.name} — {selected_policy.department}
        </strong>{' '}
        <Tag type="blue" size="sm">
          SLA {selected_policy.sakala_sla_days}d
        </Tag>
      </p>

      {/* ── Readiness Score KPI ──────────────────────────────────────────── */}
      <div style={{ marginBottom: '1rem' }}>
        <ProgressBar
          label={`Readiness Score: ${readiness_score}/100`}
          value={readiness_score}
          max={100}
          size="big"
          status={
            readiness_score >= 80 ? 'finished' : readiness_score >= 50 ? 'active' : 'error'
          }
          helperText={`${readiness_score}% application readiness`}
        />
        <div style={{ marginTop: '0.5rem' }}>
          <Tag type={statusKind} size="md">
            {status === 'READY_TO_SUBMIT' ? '✓ READY TO SUBMIT' : '⛔ BLOCKED — FIX REQUIRED'}
          </Tag>
        </div>
      </div>

      {/* ── Live Geo Verification ─────────────────────────────────────────── */}
      <div
        style={{
          background: 'var(--cds-notification-background-info, #edf5ff)',
          border: '1px solid var(--cds-notification-action-hover, #0043ce)',
          borderLeft: '3px solid var(--cds-support-info)',
          borderRadius: '2px',
          padding: '0.75rem 1rem',
          marginBottom: '1rem',
          fontSize: '0.8125rem',
        }}
      >
        <p style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.875rem' }}>
          Live Bengaluru Geo Verification
        </p>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <tbody>
            {[
              ['PIN', live_geo_check.pincode],
              ['Locality', live_geo_check.locality],
              ['Matched Ward', live_geo_check.matched_ward],
              ['GBA Zone', live_geo_check.gba_zone],
              ['ARO Office', live_geo_check.aro_office],
            ].map(([k, v]) => (
              <tr key={k}>
                <td
                  style={{
                    paddingRight: '0.75rem',
                    fontWeight: 600,
                    paddingBottom: '0.2rem',
                    verticalAlign: 'top',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {k}
                </td>
                <td style={{ paddingBottom: '0.2rem' }}>{v}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {live_geo_check.is_live_api && (
            <Tag type="teal" size="sm">
              Live India Post API
            </Tag>
          )}
          {live_geo_check.ward_mismatch && (
            <Tag type="red" size="sm">
              Ward Mismatch Detected
            </Tag>
          )}
        </div>
      </div>

      {/* ── Agent Trace Cards ─────────────────────────────────────────────── */}
      <p
        style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--cds-text-secondary)',
          marginBottom: '0.5rem',
        }}
      >
        Agent Pipeline
      </p>
      {agent_trace.map((entry, i) => (
        <AgentCard key={i} entry={entry} />
      ))}

      {/* ── Discrepancies ─────────────────────────────────────────────────── */}
      {discrepancies.length > 0 && (
        <>
          <p
            style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              color: 'var(--cds-text-secondary)',
              margin: '1rem 0 0.5rem',
            }}
          >
            Caught Discrepancies ({discrepancies.length})
          </p>
          {discrepancies.map((d, i) => (
            <DiscrepancyItem key={i} d={d} />
          ))}
        </>
      )}
    </Tile>
  )
}
