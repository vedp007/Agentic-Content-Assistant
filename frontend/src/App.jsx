import { useMemo, useRef, useState } from 'react'
import axios from 'axios'
import './App.css'

const API_URL = 'http://127.0.0.1:8000/chat'
const DICTATE_URL = 'http://127.0.0.1:8000/dictate'
const MIC_CHUNK_MS = 4500

function parseSummarySections(text = '') {
  const oneLine = text.match(/1-line summary:\s*([\s\S]*?)(?=\n\s*3 bullets:|$)/i)
  const bullets = text.match(/3 bullets:\s*([\s\S]*?)(?=\n\s*5-sentence summary:|$)/i)
  const fiveSentence = text.match(/5-sentence summary:\s*([\s\S]*)/i)

  if (!oneLine || !bullets || !fiveSentence) return null

  return {
    oneLine: oneLine[1].trim(),
    bullets: bullets[1]
      .split('\n')
      .map((item) => item.replace(/^[-*]\s*/, '').trim())
      .filter(Boolean),
    fiveSentence: fiveSentence[1].trim(),
  }
}

function parseCodeParts(text = '') {
  const parts = []
  const pattern = /```(\w+)?\n([\s\S]*?)```/g
  let cursor = 0
  let match

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      parts.push({ type: 'text', content: text.slice(cursor, match.index).trim() })
    }
    parts.push({
      type: 'code',
      language: (match[1] || 'text').toLowerCase(),
      content: match[2].trim(),
    })
    cursor = pattern.lastIndex
  }

  if (cursor < text.length) {
    parts.push({ type: 'text', content: text.slice(cursor).trim() })
  }

  return parts.filter((part) => part.content)
}

function canPreview(language, code) {
  const normalized = language.toLowerCase()
  return (
    ['html', 'css', 'js', 'javascript'].includes(normalized) ||
    /<html|<body|<div|<script|<style/i.test(code)
  )
}

function buildCombinedPreviewDocument(parts) {
  const codeParts = parts.filter((part) => part.type === 'code')
  const html = codeParts.find((part) => part.language === 'html')?.content || ''
  const css = codeParts
    .filter((part) => part.language === 'css')
    .map((part) => part.content)
    .join('\n\n')
  const js = codeParts
    .filter((part) => ['js', 'javascript'].includes(part.language))
    .map((part) => part.content)
    .join('\n\n')
  const inferredHtml = codeParts.find((part) => /<html|<body|<div|<script|<style/i.test(part.content))?.content || ''

  let documentHtml = html || inferredHtml || '<main id="app"></main>'

  if (!/<html/i.test(documentHtml)) {
    documentHtml = `<!doctype html><html><head><meta charset="utf-8"><title>Preview</title></head><body>${documentHtml}</body></html>`
  }

  if (css) {
    const styleTag = `<style>${css}</style>`
    documentHtml = /<\/head>/i.test(documentHtml)
      ? documentHtml.replace(/<\/head>/i, `${styleTag}</head>`)
      : `${styleTag}${documentHtml}`
  }

  if (js) {
    const scriptTag = `<script>${js}</script>`
    documentHtml = /<\/body>/i.test(documentHtml)
      ? documentHtml.replace(/<\/body>/i, `${scriptTag}</body>`)
      : `${documentHtml}${scriptTag}`
  }

  return documentHtml
}

function RichResponse({ text, onPreview }) {
  const parts = parseCodeParts(text)

  if (!parts.some((part) => part.type === 'code')) {
    return <p className="result-text">{text}</p>
  }

  const previewable = parts.some((part) => part.type === 'code' && canPreview(part.language, part.content))

  return (
    <div className="rich-response">
      {previewable ? (
        <div className="combined-preview-bar">
          <span>Generated code detected</span>
          <button type="button" onClick={() => onPreview(buildCombinedPreviewDocument(parts))}>
            Preview Combined
          </button>
        </div>
      ) : null}

      {parts.map((part, index) => {
        if (part.type === 'text') {
          return <p className="result-text" key={`text-${index}`}>{part.content}</p>
        }

        return (
          <div className="code-block" key={`code-${index}`}>
            <div className="code-toolbar">
              <span>{part.language}</span>
            </div>
            <pre>{part.content}</pre>
          </div>
        )
      })}
    </div>
  )
}

function FinalOutput({ text, intent, confidence, onPreview }) {
  const summary = parseSummarySections(text)

  return (
    <section className="result-panel">
      <div className="result-header">
        <h2>Final Output</h2>
        {intent ? (
          <div className="result-badges">
            <span>
              Intent: <strong>{intent.replaceAll('_', ' ')}</strong>
            </span>
            <span>
              Confidence: <strong>{typeof confidence === 'number' ? confidence.toFixed(2) : 'n/a'}</strong>
            </span>
          </div>
        ) : null}
      </div>

      {summary ? (
        <div className="summary-grid">
          <article className="summary-card">
            <div className="summary-icon purple">1</div>
            <h3>1-line Summary</h3>
            <p>{summary.oneLine}</p>
          </article>
          <article className="summary-card">
            <div className="summary-icon green">3</div>
            <h3>3 Key Points</h3>
            <ul>
              {summary.bullets.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
          <article className="summary-card">
            <div className="summary-icon blue">5</div>
            <h3>5-sentence Summary</h3>
            <p>{summary.fiveSentence}</p>
          </article>
        </div>
      ) : (
        <RichResponse text={text} onPreview={onPreview} />
      )}
    </section>
  )
}

function RobotMark({ compact = false }) {
  return (
    <div className={`robot-mark ${compact ? 'compact' : ''}`} aria-hidden="true">
      <span className="robot-antenna"></span>
      <span className="robot-ear left"></span>
      <span className="robot-ear right"></span>
      <span className="robot-head">
        <span className="robot-face">
          <span className="robot-eye"></span>
          <span className="robot-eye"></span>
        </span>
      </span>
    </div>
  )
}

function App() {
  const [message, setMessage] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [listening, setListening] = useState(false)
  const [transcribingMic, setTranscribingMic] = useState(false)
  const [micError, setMicError] = useState('')
  const [latestContext, setLatestContext] = useState('')
  const [previewHtml, setPreviewHtml] = useState('')
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const listeningRef = useRef(false)
  const chunksRef = useRef([])
  const timerRef = useRef(null)
  const [items, setItems] = useState([
    {
      role: 'agent',
      text: 'Upload a PDF, image, or audio file, use mic dictation, or ask a text question. I will plan the workflow and return text-only output.',
    },
  ])

  const canSend = useMemo(
    () => message.trim().length > 0 || file,
    [message, file],
  )

  async function sendMicChunk(blob) {
    if (!blob.size) return

    setTranscribingMic(true)
    try {
      const form = new FormData()
      form.append(
        'file',
        new File([blob], 'microphone-dictation.webm', {
          type: blob.type || 'audio/webm',
        }),
      )
      const { data } = await axios.post(DICTATE_URL, form)
      const transcript = (data.transcript || '').trim()
      if (transcript) {
        setMessage((current) => [current.trim(), transcript].filter(Boolean).join(' '))
        setMicError('')
      } else if (data.warnings?.length && !data.warnings[0].includes('no transcript')) {
        setMicError(data.warnings.join(' '))
      }
    } catch (error) {
      setMicError(`Local dictation failed: ${error.message}`)
    } finally {
      setTranscribingMic(false)
    }
  }

  function startChunkRecorder(stream) {
    const mimeType = MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : ''
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    recorderRef.current = recorder
    chunksRef.current = []

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data)
      }
    }

    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, {
        type: recorder.mimeType || 'audio/webm',
      })
      sendMicChunk(blob)
      recorderRef.current = null
      chunksRef.current = []
      if (listeningRef.current) {
        startChunkRecorder(stream)
      }
    }

    recorder.start()
    timerRef.current = window.setTimeout(() => {
      if (recorder.state !== 'inactive') {
        recorder.stop()
      }
    }, MIC_CHUNK_MS)
  }

  async function startListening() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setMicError('Local microphone dictation is not supported in this browser.')
      return
    }

    try {
      setMicError('')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      listeningRef.current = true
      setListening(true)
      startChunkRecorder(stream)
    } catch (error) {
      setMicError(`Microphone unavailable: ${error.message}`)
      listeningRef.current = false
      setListening(false)
    }
  }

  function stopListening() {
    listeningRef.current = false
    window.clearTimeout(timerRef.current)
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      recorderRef.current.stop()
    }
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setListening(false)
  }

  function toggleListening() {
    if (listening) {
      stopListening()
    } else {
      startListening()
    }
  }

  async function submit(event) {
    event.preventDefault()
    if (!canSend || loading) return

    const userText = file
      ? `${message.trim() || 'Uploaded file'}\nAttached: ${file.name}`
      : message.trim()
    setItems((current) => [...current, { role: 'user', text: userText }])
    setLoading(true)

    try {
      const form = new FormData()
      form.append('message', message)
      form.append('context', file ? '' : latestContext)
      if (file) form.append('file', file)

      const { data } = await axios.post(API_URL, form)

      setItems((current) => [
        ...current,
        {
          role: 'agent',
          text: data.response,
          extractedText: data.extracted_text,
          intent: data.intent?.intent,
          confidence: data.intent?.confidence,
          parserConfidence: data.metadata?.extraction_confidence,
          plan: data.plan || [],
          logs: data.logs || [],
          costEstimate: data.metadata?.cost_estimate,
        },
      ])
      if (data.extracted_text) {
        setLatestContext(data.extracted_text)
      }
      setMessage('')
      setFile(null)
      setMicError('')
      event.target.reset()
    } catch (error) {
      setItems((current) => [
        ...current,
        {
          role: 'agent',
          text: `I could not complete that request: ${error.message}`,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <header className="topbar">
          <div className="brand-lockup">
            <div className="brand-mark">
              <RobotMark />
            </div>
            <div>
              <h1>Agentic Content Assistant</h1>
              <p>Autonomous multimodal workflow orchestration system</p>
            </div>
          </div>
          <div className="status"><span></span> Backend Connected</div>
        </header>

        <section className="chat-window" aria-live="polite">
          {items.map((item, index) => (
            <article className={`message ${item.role}`} key={`${item.role}-${index}`}>
              {item.role === 'agent' ? (
                <div className="agent-avatar">
                  <RobotMark compact />
                </div>
              ) : null}
              <div className="message-body">
                {item.role === 'agent' ? (
                  <FinalOutput
                    text={item.text}
                    intent={item.intent}
                    confidence={item.confidence}
                    onPreview={setPreviewHtml}
                  />
                ) : (
                  <p>{item.text}</p>
                )}

                {item.extractedText ? (
                  <details>
                    <summary>
                      <span>Extracted Text</span>
                      {item.parserConfidence ? <em>Confidence: {item.parserConfidence.toFixed(2)}</em> : null}
                    </summary>
                    <pre>{item.extractedText}</pre>
                  </details>
                ) : null}

                {item.plan?.length ? (
                  <details>
                    <summary><span>Execution Plan</span></summary>
                    <ol>
                      {item.plan.map((step) => (
                        <li key={`${step.name}-${step.detail}`}>
                          <strong>{step.name}</strong>: {step.detail}
                        </li>
                      ))}
                    </ol>
                  </details>
                ) : null}

                {item.logs?.length ? (
                  <details>
                    <summary><span>Logs</span></summary>
                    <ul>
                      {item.logs.map((log) => (
                        <li key={log}>{log}</li>
                      ))}
                    </ul>
                  </details>
                ) : null}

                {item.costEstimate ? (
                  <details>
                    <summary><span>Cost Estimate</span></summary>
                    <dl className="cost-grid">
                      <div>
                        <dt>Provider</dt>
                        <dd>{item.costEstimate.provider}</dd>
                      </div>
                      <div>
                        <dt>Input tokens</dt>
                        <dd>{item.costEstimate.input_tokens_estimate}</dd>
                      </div>
                      <div>
                        <dt>Output tokens</dt>
                        <dd>{item.costEstimate.output_tokens_estimate}</dd>
                      </div>
                      <div>
                        <dt>Estimated cost</dt>
                        <dd>${item.costEstimate.estimated_cost_usd.toFixed(2)}</dd>
                      </div>
                    </dl>
                  </details>
                ) : null}
              </div>
            </article>
          ))}
          {loading ? (
            <article className="message agent">
              <div className="agent-avatar">
                <RobotMark compact />
              </div>
              <div className="message-body">
                <section className="result-panel">
                  <p className="result-text">Thinking through the plan...</p>
                </section>
              </div>
            </article>
          ) : null}
        </section>

        <form className="composer" onSubmit={submit}>
          <label className="file-picker" title="Attach file">
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp,.mp3,.wav,.m4a,.webm,.ogg,.txt"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
            <span>{file ? file.name : 'Upload File'}</span>
          </label>

          <div className="composer-field">
            <textarea
              placeholder="Type your message..."
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              rows="2"
            />
            <small>Supports: Text, PDF, JPG, PNG, MP3, WAV, M4A</small>
          </div>

          <button
            type="button"
            className={`mic-button ${listening ? 'listening' : ''}`}
            onClick={toggleListening}
            disabled={loading}
          >
            {listening ? 'Stop Mic' : transcribingMic ? 'Transcribing' : 'Mic'}
          </button>

          <button className="send-button" type="submit" disabled={!canSend || loading}>
            {loading ? '...' : '↑'}
          </button>

          {micError ? <p className="composer-error">{micError}</p> : null}
          {listening || transcribingMic ? (
            <p className="composer-hint">
              {listening
                ? 'Listening locally. Words are added after each short audio chunk.'
                : 'Converting speech to text...'}
            </p>
          ) : null}
        </form>

        {previewHtml ? (
          <div className="preview-overlay" role="dialog" aria-modal="true" aria-label="Code preview">
            <section className="preview-panel">
              <header>
                <h2>Preview</h2>
                <button type="button" onClick={() => setPreviewHtml('')}>Close</button>
              </header>
              <iframe title="Code preview" sandbox="allow-scripts" srcDoc={previewHtml}></iframe>
            </section>
          </div>
        ) : null}
      </section>
    </main>
  )
}

export default App
