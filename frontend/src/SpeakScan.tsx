// ─────────────────────────────────────────────────────────────────────────────
// Column 1 — Speak & Scan: Voice AI + Vision OCR + Run Audit CTA
// ─────────────────────────────────────────────────────────────────────────────
import { useCallback, useRef, useState } from 'react'
import {
  Button,
  Dropdown,
  FileUploaderDropContainer,
  InlineLoading,
  InlineNotification,
  StructuredListBody,
  StructuredListCell,
  StructuredListHead,
  StructuredListRow,
  StructuredListWrapper,
  Tag,
  TextArea,
  Tile,
} from '@carbon/react'
import { ArrowRight, Microphone, MicrophoneOff, Upload } from '@carbon/icons-react'
import { API_BASE } from './types'
import type {
  OrchestrateRequest,
  OrchestrateResponse,
  VisionExtractResponse,
  VisualFlag,
} from './types'

// ── Types for SpeechRecognition (not in lib.dom yet for all setups) ──────────
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
}
interface SpeechRecognitionInstance extends EventTarget {
  lang: string
  continuous: boolean
  interimResults: boolean
  start(): void
  stop(): void
  onresult: ((e: SpeechRecognitionEvent) => void) | null
  onend: (() => void) | null
  onerror: ((e: Event) => void) | null
}
declare const SpeechRecognition: new () => SpeechRecognitionInstance
declare const webkitSpeechRecognition: new () => SpeechRecognitionInstance

const LANGUAGES = [
  { id: 'en-IN', text: 'English (en-IN)' },
  { id: 'kn-IN', text: 'ಕನ್ನಡ (kn-IN)' },
  { id: 'hi-IN', text: 'हिन्दी (hi-IN)' },
]

const DEMO_PRESETS = [
  {
    label: 'e-Khata Mismatch (Mahadevapura)',
    query:
      'My e-Khata mutation is rejected. Applicant name R. Kumar does not match property document Ramesh Kumar. Pincode 560001.',
    sampleCaseId: 'ekhata_mismatch',
    policyId: 'ekhata',
  },
  {
    label: 'BESCOM Gruha Jyothi Tenant (HSR)',
    query:
      'I want to apply for Gruha Jyothi electricity subsidy in HSR Layout Koramangala, pincode 560034. My monthly units are 253.',
    sampleCaseId: 'gruha_jyothi_tenant',
    policyId: 'gruha_jyothi',
  },
  {
    label: 'Sakala SLA Delay Appeal (Hebbal)',
    query:
      'My Sakala service request filed on 2026-04-01 from Whitefield pincode 560066 has not been processed. The SLA deadline has passed.',
    sampleCaseId: 'sakala_sla_breach',
    policyId: 'sakala',
  },
]

interface Props {
  onResult: (result: OrchestrateResponse) => void
}

export default function SpeakScan({ onResult }: Props) {
  const [language, setLanguage] = useState<'en-IN' | 'kn-IN' | 'hi-IN'>(
    'en-IN',
  )
  const [transcript, setTranscript] = useState('')
  const [listening, setListening] = useState(false)
  const [visionResult, setVisionResult] =
    useState<VisionExtractResponse | null>(null)
  const [visionLoading, setVisionLoading] = useState(false)
  const [visionError, setVisionError] = useState('')
  const [runLoading, setRunLoading] = useState(false)
  const [runError, setRunError] = useState('')
  const [activePolicyId, setActivePolicyId] = useState('auto')
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)

  // ── Voice AI ───────────────────────────────────────────────────────────────
  function toggleListening() {
    if (listening) {
      recognitionRef.current?.stop()
      setListening(false)
      return
    }
    const SpeechRecognitionCtor =
      (typeof SpeechRecognition !== 'undefined' && SpeechRecognition) ||
      (typeof webkitSpeechRecognition !== 'undefined' &&
        webkitSpeechRecognition) ||
      null
    if (!SpeechRecognitionCtor) {
      setRunError(
        'Web Speech API not supported in this browser. Use Chrome or Edge.',
      )
      return
    }
    const rec = new SpeechRecognitionCtor()
    rec.lang = language
    rec.continuous = true
    rec.interimResults = true
    rec.onresult = (e: SpeechRecognitionEvent) => {
      let final = ''
      for (let i = 0; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript + ' '
      }
      if (final.trim()) setTranscript((prev) => prev + final)
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    rec.start()
    recognitionRef.current = rec
    setListening(true)
  }

  // ── Demo Preset ────────────────────────────────────────────────────────────
  async function loadPreset(preset: (typeof DEMO_PRESETS)[0]) {
    setTranscript(preset.query)
    setActivePolicyId(preset.policyId)
    setVisionError('')
    setRunError('')
    setVisionLoading(true)
    try {
      const res = await fetch(
        `${API_BASE}/vision-extract?sample_case_id=${preset.sampleCaseId}`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error(res.statusText)
      const data: VisionExtractResponse = await res.json()
      setVisionResult(data)
    } catch (e: unknown) {
      setVisionError((e as Error).message)
    } finally {
      setVisionLoading(false)
    }
  }

  // ── File Upload ────────────────────────────────────────────────────────────
  const handleFileUpload = useCallback(
    async (files: File[]) => {
      if (!files.length) return
      setVisionLoading(true)
      setVisionError('')
      setVisionResult(null)
      const formData = new FormData()
      formData.append('file', files[0])
      try {
        const res = await fetch(`${API_BASE}/vision-extract`, {
          method: 'POST',
          body: formData,
        })
        if (!res.ok) throw new Error(await res.text())
        setVisionResult(await res.json())
      } catch (e: unknown) {
        setVisionError((e as Error).message)
      } finally {
        setVisionLoading(false)
      }
    },
    [],
  )

  // ── Run Audit ──────────────────────────────────────────────────────────────
  async function runAudit() {
    setRunLoading(true)
    setRunError('')
    const body: OrchestrateRequest = {
      query: transcript,
      language,
      extracted_fields: visionResult?.extracted_fields ?? {},
      visual_flags: visionResult?.visual_flags ?? [],
      policy_id: activePolicyId,
    }
    try {
      const res = await fetch(`${API_BASE}/orchestrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      const data: OrchestrateResponse = await res.json()
      onResult(data)
    } catch (e: unknown) {
      setRunError((e as Error).message)
    } finally {
      setRunLoading(false)
    }
  }

  // ── Render helpers ─────────────────────────────────────────────────────────
  function efRow(label: string, value: string | number | null | undefined) {
    if (value === null || value === undefined || value === '') return null
    return (
      <StructuredListRow key={label}>
        <StructuredListCell noWrap style={{ fontWeight: 600, width: '45%' }}>
          {label}
        </StructuredListCell>
        <StructuredListCell>{String(value)}</StructuredListCell>
      </StructuredListRow>
    )
  }

  const ef = visionResult?.extracted_fields

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
        Speak &amp; Scan
      </h4>

      {/* ── Language Switcher ─────────────────────────────────────────────── */}
      <Dropdown
        id="language-dropdown"
        titleText="Language"
        label="Select language"
        items={LANGUAGES}
        itemToString={(item) => item?.text ?? ''}
        selectedItem={LANGUAGES.find((l) => l.id === language) ?? LANGUAGES[0]}
        onChange={({ selectedItem }) => {
          if (selectedItem) setLanguage(selectedItem.id as typeof language)
        }}
        style={{ marginBottom: '0.75rem' }}
      />

      {/* ── Voice Input ──────────────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '0.5rem',
        }}
      >
        <Button
          kind={listening ? 'danger' : 'secondary'}
          size="md"
          renderIcon={listening ? MicrophoneOff : Microphone}
          onClick={toggleListening}
          hasIconOnly={false}
        >
          {listening ? 'Stop' : 'Speak'}
        </Button>
        {listening && (
          <Tag type="red" size="md">
            Listening…
          </Tag>
        )}
      </div>

      <TextArea
        id="transcript-textarea"
        labelText="Query / Transcript"
        placeholder="Speak or type your civic query here…"
        value={transcript}
        onChange={(e) => setTranscript(e.target.value)}
        rows={4}
        style={{ marginBottom: '1rem' }}
      />

      {/* ── Demo Presets ──────────────────────────────────────────────────── */}
      <p
        style={{
          fontSize: '0.75rem',
          color: 'var(--cds-text-secondary)',
          marginBottom: '0.5rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
        }}
      >
        One-Click Demo Presets
      </p>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
          marginBottom: '1.25rem',
        }}
      >
        {DEMO_PRESETS.map((p) => (
          <Button
            key={p.sampleCaseId}
            kind="tertiary"
            size="sm"
            onClick={() => loadPreset(p)}
          >
            {p.label}
          </Button>
        ))}
      </div>

      {/* ── Vision OCR Drop Zone ──────────────────────────────────────────── */}
      <p
        style={{
          fontSize: '0.75rem',
          color: 'var(--cds-text-secondary)',
          marginBottom: '0.5rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
        }}
      >
        Vision OCR — Upload Document
      </p>
      <FileUploaderDropContainer
        accept={['image/png', 'image/jpeg']}
        labelText="Drag & drop or click to upload civic document (PNG / JPG)"
        multiple={false}
        onAddFiles={(_e, { addedFiles }) => {
          void handleFileUpload(addedFiles)
        }}
        style={{ marginBottom: '0.75rem' }}
      />
      {visionLoading && (
        <InlineLoading description="Extracting document fields…" />
      )}
      {visionError && (
        <InlineNotification
          kind="error"
          lowContrast
          hideCloseButton
          title="Vision Error"
          subtitle={visionError}
          style={{ marginBottom: '0.5rem' }}
        />
      )}

      {/* ── Extracted Fields ─────────────────────────────────────────────── */}
      {visionResult && ef && (
        <div style={{ marginBottom: '1rem' }}>
          <p
            style={{
              fontSize: '0.75rem',
              color: 'var(--cds-text-secondary)',
              marginBottom: '0.5rem',
              fontWeight: 600,
            }}
          >
            Extracted Fields &nbsp;
            <span style={{ color: 'var(--cds-text-secondary)', fontWeight: 400 }}>
              ({visionResult.document_type}) — confidence{' '}
              {Math.round(visionResult.confidence * 100)}%
            </span>
          </p>
          <StructuredListWrapper>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Field</StructuredListCell>
                <StructuredListCell head>Value</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {efRow('Applicant Name', ef.applicant_name)}
              {efRow('Doc Owner Name', ef.doc_owner_name)}
              {efRow('Account / PID', ef.account_or_pid)}
              {efRow('Pincode', ef.pincode)}
              {efRow('Ward Claimed', ef.ward_claimed)}
              {efRow('Built-up Area (sqft)', ef.built_up_area_sqft)}
              {efRow('Monthly Units', ef.monthly_units)}
              {efRow('Application Date', ef.application_date)}
            </StructuredListBody>
          </StructuredListWrapper>

          {/* Visual flags */}
          {visionResult.visual_flags.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '0.5rem',
                marginTop: '0.5rem',
              }}
            >
              {visionResult.visual_flags.map((f: VisualFlag, i: number) => (
                <Tag key={i} type="red" size="md">
                  {f.severity.toUpperCase()}: {f.issue.slice(0, 60)}
                  {f.issue.length > 60 ? '…' : ''}
                </Tag>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Run Audit CTA ─────────────────────────────────────────────────── */}
      {runError && (
        <InlineNotification
          kind="error"
          lowContrast
          hideCloseButton
          title="Orchestration Error"
          subtitle={runError}
          style={{ marginBottom: '0.75rem' }}
        />
      )}
      <Button
        kind="primary"
        renderIcon={runLoading ? undefined : ArrowRight}
        onClick={() => void runAudit()}
        disabled={runLoading || (!transcript.trim() && !visionResult)}
        style={{ width: '100%', maxWidth: '100%', justifyContent: 'center' }}
      >
        {runLoading ? (
          <InlineLoading
            description="Running 4-Agent Pre-Flight Audit…"
            style={{ color: 'white' }}
          />
        ) : (
          'Run 4-Agent Pre-Flight Audit'
        )}
      </Button>
      {/* Upload icon only used as import sanity — referenced in FileUploader area label visually */}
      <span style={{ display: 'none' }}>
        <Upload />
      </span>
    </Tile>
  )
}
