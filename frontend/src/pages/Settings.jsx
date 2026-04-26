import { useEffect, useState } from 'react'
import { getWatchlist, updateWatchlist, getMode, setMode } from '../api/endpoints'

function Section({ title, children }) {
  return (
    <div className="bg-gray-900 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-400 mb-4">{title}</h2>
      {children}
    </div>
  )
}

function WatchlistManager() {
  const [symbols, setSymbols] = useState([])
  const [input, setInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    getWatchlist().then(r => setSymbols(r.data.symbols)).catch(() => {})
  }, [])

  const add = () => {
    const cleaned = input.trim().toUpperCase().split(/[\s,]+/).filter(Boolean)
    const next = [...new Set([...symbols, ...cleaned])]
    setSymbols(next)
    setInput('')
  }

  const remove = (sym) => setSymbols(symbols.filter(s => s !== sym))

  const save = async () => {
    setSaving(true)
    setStatus(null)
    try {
      await updateWatchlist(symbols)
      setStatus({ ok: true, msg: 'Watchlist saved. New symbols will be backfilled on the next scheduled run.' })
    } catch (e) {
      setStatus({ ok: false, msg: e?.response?.data?.detail || 'Save failed' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 min-h-[2rem]">
        {symbols.length === 0 && <span className="text-xs text-gray-600">No symbols</span>}
        {symbols.map(sym => (
          <span
            key={sym}
            className="inline-flex items-center gap-1.5 bg-gray-800 text-gray-200 text-sm px-3 py-1 rounded-full"
          >
            {sym}
            <button
              onClick={() => remove(sym)}
              className="text-gray-500 hover:text-red-400 transition-colors leading-none"
            >
              ×
            </button>
          </span>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          placeholder="AAPL, MSFT, NVDA…"
          className="flex-1 bg-gray-800 border border-gray-700 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-sky-600 placeholder-gray-600"
        />
        <button
          onClick={add}
          className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-4 py-2 rounded-lg transition-colors"
        >
          Add
        </button>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={save}
          disabled={saving}
          className="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
        >
          {saving ? 'Saving…' : 'Save Watchlist'}
        </button>
        {status && (
          <span className={`text-xs ${status.ok ? 'text-green-400' : 'text-red-400'}`}>
            {status.msg}
          </span>
        )}
      </div>
    </div>
  )
}

function ModeManager() {
  const [mode, setModeState] = useState(null)
  const [liveEnabled, setLiveEnabled] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    getMode().then(r => {
      setModeState(r.data.mode)
      setLiveEnabled(r.data.live_enabled)
    }).catch(() => {})
  }, [])

  const switchMode = async (target) => {
    if (target === 'live') {
      const confirm = window.prompt('Type I_UNDERSTAND_RISK to switch to live trading:')
      if (confirm !== 'I_UNDERSTAND_RISK') {
        setStatus({ ok: false, msg: 'Confirmation text did not match — mode unchanged.' })
        return
      }
      setSaving(true)
      try {
        await setMode('live', 'I_UNDERSTAND_RISK')
        setModeState('live')
        setStatus({ ok: true, msg: 'Switched to live trading.' })
      } catch (e) {
        setStatus({ ok: false, msg: e?.response?.data?.detail || 'Failed to switch mode' })
      } finally {
        setSaving(false)
      }
    } else {
      setSaving(true)
      try {
        await setMode('paper', '')
        setModeState('paper')
        setStatus({ ok: true, msg: 'Switched to paper trading.' })
      } catch (e) {
        setStatus({ ok: false, msg: e?.response?.data?.detail || 'Failed to switch mode' })
      } finally {
        setSaving(false)
      }
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-3">
        {['paper', 'live'].map(m => (
          <button
            key={m}
            disabled={saving || mode === m || (m === 'live' && !liveEnabled)}
            onClick={() => switchMode(m)}
            className={`px-5 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 ${
              mode === m
                ? m === 'live' ? 'bg-red-600 text-white' : 'bg-sky-600 text-white'
                : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
            }`}
          >
            {m === mode ? `${m.toUpperCase()} (active)` : m.toUpperCase()}
          </button>
        ))}
      </div>
      {!liveEnabled && (
        <p className="text-xs text-gray-600">Live trading requires <code className="text-gray-500">ALPACA_LIVE_ENABLED=true</code> in .env + backend restart.</p>
      )}
      {status && (
        <p className={`text-xs ${status.ok ? 'text-green-400' : 'text-red-400'}`}>{status.msg}</p>
      )}
    </div>
  )
}

export default function Settings() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      <Section title="Watchlist">
        <p className="text-xs text-gray-500 mb-4">
          These are the symbols the system monitors, generates signals for, and (when enabled) trades.
          Type one or more tickers separated by commas or spaces, then click Add and Save.
        </p>
        <WatchlistManager />
      </Section>

      <Section title="Trading Mode">
        <p className="text-xs text-gray-500 mb-4">
          Paper mode simulates trades with no real money. Live mode requires Alpaca API keys and explicit confirmation.
        </p>
        <ModeManager />
      </Section>
    </div>
  )
}
