// ─────────────────────────────────────────────────────────────────────────────
// AppHeader — Carbon UI Shell header with live policy count + register modal
// ─────────────────────────────────────────────────────────────────────────────
import { useEffect, useRef, useState } from 'react'
import {
  Button,
  Header,
  HeaderGlobalBar,
  HeaderName,
  InlineLoading,
  Modal,
  Tag,
  TextArea,
} from '@carbon/react'
import { Add } from '@carbon/icons-react'
import { API_BASE } from './types'
import type { PolicyRegisterResponse, PolicySummary } from './types'

interface Props {
  policies: PolicySummary[]
  onPoliciesUpdated: () => void
}

const E_SWATHU_STUB = JSON.stringify(
  {
    id: 'e_swathu_form11a',
    name: 'e-Swathu Form 11A — Rural Property Conversion',
    department: 'Revenue / AHD',
    sakala_sla_days: 30,
    version: '1.0.0',
    keywords: [
      'e-swathu',
      'form 11a',
      'eswathu',
      'revenue site',
      'conversion certificate',
      'ಇ-ಸ್ವತ್ತು',
    ],
    validation_rules: [
      {
        rule_id: 'name_match',
        field: 'applicant_name',
        check: 'fuzzy_name_match',
        severity: 'critical',
        message: 'Applicant name must match property owner on Form 11A',
        remediation: 'Submit an affidavit with notarised name correction.',
      },
    ],
  },
  null,
  2,
)

export default function AppHeader({ policies, onPoliciesUpdated }: Props) {
  const [modalOpen, setModalOpen] = useState(false)
  const [jsonText, setJsonText] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const textAreaRef = useRef<HTMLTextAreaElement>(null)

  // reset state when modal opens
  useEffect(() => {
    if (modalOpen) {
      setJsonText('')
      setError('')
      setSuccess('')
    }
  }, [modalOpen])

  async function handleRegister() {
    setLoading(true)
    setError('')
    setSuccess('')
    let body: unknown
    try {
      body = JSON.parse(jsonText)
    } catch {
      setError('Invalid JSON — please check your input.')
      setLoading(false)
      return
    }
    try {
      const res = await fetch(`${API_BASE}/policies/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        setError(`API error: ${err?.detail ?? res.statusText}`)
      } else {
        const data: PolicyRegisterResponse = await res.json()
        setSuccess(
          `✓ Registered "${data.policy_id}" — ${data.total_policies} packs active`,
        )
        onPoliciesUpdated()
      }
    } catch (e: unknown) {
      setError(`Network error: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Header aria-label="SevaSync BLR">
        <HeaderName href="#" prefix="IBM Bobathon">
          SevaSync BLR
        </HeaderName>
        <HeaderGlobalBar>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              paddingRight: '1rem',
            }}
          >
            <Tag type="blue" size="md">
              {policies.length} Civic Policy Packs Active
            </Tag>
            <Button
              kind="primary"
              size="md"
              renderIcon={Add}
              onClick={() => setModalOpen(true)}
            >
              Plug-in New Service
            </Button>
          </div>
        </HeaderGlobalBar>
      </Header>

      <Modal
        open={modalOpen}
        modalHeading="Register New Civic Policy Pack"
        primaryButtonText={loading ? 'Registering…' : 'Register Policy Pack'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={loading || !jsonText.trim()}
        onRequestSubmit={handleRegister}
        onRequestClose={() => setModalOpen(false)}
        onSecondarySubmit={() => setModalOpen(false)}
        size="lg"
      >
        <p
          style={{
            marginBottom: '1rem',
            color: 'var(--cds-text-secondary)',
            fontSize: '0.875rem',
          }}
        >
          Paste a full PolicyPack JSON object to hot-load it into the live
          registry without restarting the server (Civic-as-Code).
        </p>

        <Button
          kind="tertiary"
          size="sm"
          style={{ marginBottom: '1rem' }}
          onClick={() => {
            setJsonText(E_SWATHU_STUB)
            setTimeout(() => textAreaRef.current?.focus(), 50)
          }}
        >
          Load e-Swathu Form 11A JSON
        </Button>

        <TextArea
          ref={textAreaRef}
          id="policy-json-input"
          labelText="Policy Pack JSON"
          placeholder='{"id": "my_policy", "name": "...", ...}'
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          rows={12}
          style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
        />

        {error && (
          <p
            style={{
              color: 'var(--cds-support-error)',
              marginTop: '0.5rem',
              fontSize: '0.8125rem',
            }}
          >
            {error}
          </p>
        )}
        {success && (
          <p
            style={{
              color: 'var(--cds-support-success)',
              marginTop: '0.5rem',
              fontSize: '0.8125rem',
            }}
          >
            {success}
          </p>
        )}
        {loading && (
          <InlineLoading
            description="Registering policy pack…"
            style={{ marginTop: '0.5rem' }}
          />
        )}
      </Modal>
    </>
  )
}
