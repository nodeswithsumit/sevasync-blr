// ─────────────────────────────────────────────────────────────────────────────
// App.tsx — SevaSync BLR root layout
// 3-column Carbon Grid: Speak & Scan | Agent Trace | Solve & Scale
// ─────────────────────────────────────────────────────────────────────────────
import { useCallback, useEffect, useState } from 'react'
import { Column, Grid, Theme } from '@carbon/react'
import AppHeader from './AppHeader'
import AgentTrace from './AgentTrace'
import SolveScale from './SolveScale'
import SpeakScan from './SpeakScan'
import { API_BASE } from './types'
import type { OrchestrateResponse, PoliciesResponse, PolicySummary } from './types'

export default function App() {
  const [policies, setPolicies] = useState<PolicySummary[]>([])
  const [result, setResult] = useState<OrchestrateResponse | null>(null)

  const fetchPolicies = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/policies`)
      if (res.ok) {
        const data: PoliciesResponse = await res.json()
        setPolicies(data.policies)
      }
    } catch {
      // backend may not be up yet — fail silently
    }
  }, [])

  useEffect(() => {
    void fetchPolicies()
  }, [fetchPolicies])

  return (
    <Theme theme="g10">
      {/* ── Shell Header ──────────────────────────────────────────────────── */}
      <AppHeader policies={policies} onPoliciesUpdated={() => void fetchPolicies()} />

      {/* ── Page Body ─────────────────────────────────────────────────────── */}
      <main
        style={{
          marginTop: '3rem', // push below 48px Carbon header
          minHeight: 'calc(100vh - 3rem)',
          background: 'var(--cds-background)',
          padding: '1.5rem 0',
        }}
      >
        <Grid fullWidth>
          {/* Column 1 — Speak & Scan */}
          <Column lg={5} md={4} sm={4} style={{ marginBottom: '1.5rem' }}>
            <SpeakScan onResult={setResult} />
          </Column>

          {/* Column 2 — Live 4-Agent Reasoning Trace */}
          <Column lg={6} md={4} sm={4} style={{ marginBottom: '1.5rem' }}>
            <AgentTrace result={result} />
          </Column>

          {/* Column 3 — Solve & Scale */}
          <Column lg={5} md={8} sm={4} style={{ marginBottom: '1.5rem' }}>
            <SolveScale result={result} />
          </Column>
        </Grid>
      </main>
    </Theme>
  )
}
