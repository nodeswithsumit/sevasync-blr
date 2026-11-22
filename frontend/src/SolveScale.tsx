// ─────────────────────────────────────────────────────────────────────────────
// Column 3 — Solve & Scale: Fix Checklist + Bilingual Draft + Sandbox Submit
// ─────────────────────────────────────────────────────────────────────────────
import { useState } from 'react'
import {
  Button,
  Checkbox,
  CodeSnippet,
  InlineLoading,
  InlineNotification,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Tile,
} from '@carbon/react'
import { Send, VolumeUp } from '@carbon/icons-react'
import { API_BASE } from './types'
import type {
  OrchestrateResponse,
  SandboxSubmitRequest,
  SandboxSubmitResponse,
} from './types'

interface Props {
  result: OrchestrateResponse | null
}

export default function SolveScale({ result }: Props) {
  const [checkedItems, setCheckedItems] = useState<Record<number, boolean>>({})
  const [submitLoading, setSubmitLoading] = useState(false)
  const [submitResult, setSubmitResult] = useState<SandboxSubmitResponse | null>(null)
  const [submitError, setSubmitError] = useState('')
  const [speaking, setSpeaking] = useState<'en' | 'kn' | null>(null)

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
          Solve &amp; Scale
        </h4>
        <p style={{ color: 'var(--cds-text-secondary)', fontSize: '0.875rem' }}>
          Actionable outputs will appear here after running the Pre-Flight Audit.
        </p>
      </Tile>
    )
  }

  const { fix_checklist, bilingual_draft, sandbox_payload, selected_policy } = result

  function toggleCheck(i: number) {
    setCheckedItems((prev) => ({ ...prev, [i]: !prev[i] }))
  }

  function readAloud(text: string, lang: 'en-IN' | 'kn-IN', key: 'en' | 'kn') {
    if (!window.speechSynthesis) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = lang
    utterance.rate = 0.9
    utterance.onend = () => setSpeaking(null)
    utterance.onerror = () => setSpeaking(null)
    setSpeaking(key)
    window.speechSynthesis.speak(utterance)
  }

  async function handleSubmit() {
    setSubmitLoading(true)
    setSubmitError('')
    setSubmitResult(null)
    const body: SandboxSubmitRequest = {
      policy_id: selected_policy.id,
      payload: sandbox_payload,
    }
    try {
      const res = await fetch(`${API_BASE}/sandbox/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      setSubmitResult(await res.json())
    } catch (e: unknown) {
      setSubmitError((e as Error).message)
    } finally {
      setSubmitLoading(false)
    }
  }

  const checkedCount = Object.values(checkedItems).filter(Boolean).length

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
        Solve &amp; Scale
      </h4>

      {/* ── Fix Checklist ─────────────────────────────────────────────────── */}
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
        Fix Checklist &nbsp;
        <span style={{ color: 'var(--cds-text-primary)', fontWeight: 400, textTransform: 'none' }}>
          ({checkedCount}/{fix_checklist.length} resolved)
        </span>
      </p>

      <div style={{ marginBottom: '1.25rem' }}>
        {fix_checklist.map((item, i) => (
          <Checkbox
            key={i}
            id={`fix-item-${i}`}
            labelText={item}
            checked={checkedItems[i] ?? false}
            onChange={() => toggleCheck(i)}
            style={{ marginBottom: '0.5rem' }}
          />
        ))}
        {fix_checklist.length === 0 && (
          <p style={{ color: 'var(--cds-text-secondary)', fontSize: '0.875rem' }}>
            No fixes required — application is ready to submit.
          </p>
        )}
      </div>

      {/* ── Bilingual Draft Viewer ─────────────────────────────────────────── */}
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
        Bilingual Draft — {bilingual_draft.document_title}
      </p>

      <div style={{ marginBottom: '1.25rem' }}>
      <Tabs>
        <TabList aria-label="Bilingual draft language tabs">
          <Tab>English</Tab>
          <Tab>ಕನ್ನಡ (Kannada)</Tab>
        </TabList>
        <TabPanels>
          {/* English */}
          <TabPanel>
            <div style={{ fontSize: '0.8125rem', maxHeight: '220px', overflow: 'auto' }}>
            <CodeSnippet
              type="multi"
              feedback="Copied!"
            >
              {bilingual_draft.english}
            </CodeSnippet>
            </div>
            <Button
              kind="secondary"
              size="sm"
              renderIcon={speaking === 'en' ? undefined : VolumeUp}
              style={{ marginTop: '0.5rem' }}
              onClick={() => {
                if (speaking === 'en') {
                  window.speechSynthesis?.cancel()
                  setSpeaking(null)
                } else {
                  readAloud(bilingual_draft.english, 'en-IN', 'en')
                }
              }}
            >
              {speaking === 'en' ? (
                <InlineLoading description="Reading aloud…" />
              ) : (
                'Read Aloud'
              )}
            </Button>
          </TabPanel>

          {/* Kannada */}
          <TabPanel>
            <div style={{ maxHeight: '220px', overflow: 'auto' }}>
            <CodeSnippet
              type="multi"
              feedback="Copied!"
            >
              {bilingual_draft.kannada}
            </CodeSnippet>
            </div>
            <Button
              kind="secondary"
              size="sm"
              renderIcon={speaking === 'kn' ? undefined : VolumeUp}
              style={{ marginTop: '0.5rem' }}
              onClick={() => {
                if (speaking === 'kn') {
                  window.speechSynthesis?.cancel()
                  setSpeaking(null)
                } else {
                  readAloud(bilingual_draft.kannada, 'kn-IN', 'kn')
                }
              }}
            >
              {speaking === 'kn' ? (
                <InlineLoading description="Reading aloud…" />
              ) : (
                'Read Aloud'
              )}
            </Button>
          </TabPanel>
        </TabPanels>
      </Tabs>
      </div>

      {/* ── Sandbox Submission ────────────────────────────────────────────── */}
      <p
        style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--cds-text-secondary)',
          marginBottom: '0.75rem',
        }}
      >
        API Setu Sandbox Submission
      </p>

      {submitResult ? (
        <div
          style={{
            background: 'var(--cds-notification-background-success, #defbe6)',
            border: '1px solid var(--cds-support-success)',
            borderLeft: '3px solid var(--cds-support-success)',
            borderRadius: '2px',
            padding: '0.75rem 1rem',
            marginBottom: '0.75rem',
            fontSize: '0.8125rem',
          }}
        >
          <p style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.875rem', color: 'var(--cds-support-success)' }}>
            ✓ Submitted Successfully
          </p>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <tbody>
              {[
                ['GSC Tracking ID', submitResult.sakala_gsc_id],
                ['Submitted At', new Date(submitResult.submitted_at).toLocaleString('en-IN')],
                ['SLA Deadline', `${submitResult.sla_deadline_days} working days`],
                ['Adapter', submitResult.adapter],
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
                  <td
                    style={{
                      paddingBottom: '0.2rem',
                      fontFamily: k === 'GSC Tracking ID' ? 'monospace' : 'inherit',
                      fontWeight: k === 'GSC Tracking ID' ? 600 : 400,
                    }}
                  >
                    {v}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {submitError && (
        <InlineNotification
          kind="error"
          lowContrast
          hideCloseButton
          title="Submission Error"
          subtitle={submitError}
          style={{ maxWidth: '100%', marginBottom: '0.75rem' }}
        />
      )}

      <Button
        kind="primary"
        renderIcon={submitLoading ? undefined : Send}
        onClick={() => void handleSubmit()}
        disabled={submitLoading}
        style={{ width: '100%', maxWidth: '100%', justifyContent: 'center' }}
      >
        {submitLoading ? (
          <InlineLoading description="Submitting to API Setu Sandbox…" style={{ color: 'white' }} />
        ) : (
          'Submit to API Setu Sandbox'
        )}
      </Button>
    </Tile>
  )
}
