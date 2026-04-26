import { useEffect, useState } from 'react'
import { getRankedSignals } from '../api/endpoints'

function ScoreBar({ value }) {
  const pct = value != null ? (Number(value) * 100).toFixed(1) : null
  if (pct == null) return null
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-400 mb-1">
        <span>Score</span>
        <span className="text-sky-400 font-semibold">{pct}%</span>
      </div>
      <div className="w-full bg-gray-800 rounded-full h-2">
        <div
          className="bg-gradient-to-r from-sky-600 to-sky-400 h-2 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

function Pill({ label, value, suffix = '' }) {
  if (value == null || value === '') return null
  return (
    <span className="inline-flex items-center gap-1 bg-gray-800 text-gray-300 text-xs px-2 py-1 rounded-full">
      <span className="text-gray-500">{label}</span>
      <span>{typeof value === 'number' ? value.toFixed(2) : value}{suffix}</span>
    </span>
  )
}

function TechnicalDetail({ ki }) {
  const rows = [
    { label: 'RSI(14)', value: ki.rsi_14 != null ? Number(ki.rsi_14).toFixed(1) : null },
    { label: 'MACD Trend', value: ki.macd_trend },
    { label: 'BB %B', value: ki.bb_pct_b != null ? Number(ki.bb_pct_b).toFixed(3) : null },
    { label: 'ADX(14)', value: ki.adx_14 != null ? Number(ki.adx_14).toFixed(1) : null },
    { label: '20d Momentum', value: ki.momentum_20d != null ? `${(Number(ki.momentum_20d) * 100).toFixed(2)}%` : null },
  ].filter(r => r.value != null)

  if (!rows.length) return <div className="text-xs text-gray-600 mt-2">No technical data</div>

  return (
    <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1">
      {rows.map(({ label, value }) => (
        <div key={label} className="flex justify-between text-xs">
          <span className="text-gray-500">{label}</span>
          <span className={`font-mono ${value === 'bullish' ? 'text-green-400' : value === 'bearish' ? 'text-red-400' : 'text-gray-300'}`}>{value}</span>
        </div>
      ))}
    </div>
  )
}

function RankedCard({ rank, rec }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-gray-900 rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl font-black text-gray-600 w-8 text-center">#{rank}</span>
          <div>
            <div className="font-bold text-white text-lg leading-tight">{rec.symbol}</div>
            {rec.sector && <div className="text-xs text-gray-500 mt-0.5">{rec.sector}</div>}
          </div>
        </div>
        <span className="inline-block px-3 py-1 rounded-full text-sm font-bold text-green-400 bg-green-900/40">
          BUY
        </span>
      </div>

      <ScoreBar value={rec.composite_score} />

      <div className="flex flex-wrap gap-2">
        <Pill label="P/E" value={rec.pe_ratio != null ? Number(rec.pe_ratio) : null} />
        <Pill label="Fwd P/E" value={rec.forward_pe != null ? Number(rec.forward_pe) : null} />
        <Pill label="Beta" value={rec.beta != null ? Number(rec.beta) : null} />
        <Pill label="Target" value={rec.analyst_target_price != null ? `$${Number(rec.analyst_target_price).toFixed(2)}` : null} label2="" />
        <Pill label="52W High" value={rec.week_52_high != null ? `$${Number(rec.week_52_high).toFixed(2)}` : null} label2="" />
        <Pill label="52W Low" value={rec.week_52_low != null ? `$${Number(rec.week_52_low).toFixed(2)}` : null} label2="" />
      </div>

      {rec.rationale && (
        <p className="text-sm text-gray-400 italic border-l-2 border-sky-700 pl-3">
          {rec.rationale}
        </p>
      )}

      <button
        onClick={() => setExpanded(v => !v)}
        className="text-xs text-sky-500 hover:text-sky-400 self-start transition-colors"
      >
        {expanded ? 'Hide' : 'Show'} technical indicators
      </button>

      {expanded && <TechnicalDetail ki={rec.key_indicators} />}

      <div className="flex justify-between text-xs text-gray-600 border-t border-gray-800 pt-2">
        <span>{(Number(rec.confidence) * 100).toFixed(1)}% ML confidence</span>
        <span>{new Date(rec.generated_at).toLocaleString()}</span>
      </div>
    </div>
  )
}

export default function Recommendations() {
  const [recs, setRecs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [limit, setLimit] = useState(20)

  const load = async (l) => {
    setLoading(true)
    setError(null)
    try {
      const res = await getRankedSignals(l)
      setRecs(res.data)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load recommendations')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(limit) }, [limit])

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Recommendations</h1>
          <p className="text-sm text-gray-500 mt-1">Ranked BUY signals by composite score (today)</p>
        </div>
        <select
          value={limit}
          onChange={e => setLimit(Number(e.target.value))}
          className="bg-gray-800 text-gray-300 text-sm rounded-lg px-3 py-1.5 border border-gray-700 focus:outline-none focus:ring-1 focus:ring-sky-600"
        >
          {[5, 10, 20, 50].map(n => (
            <option key={n} value={n}>Top {n}</option>
          ))}
        </select>
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {!loading && !error && recs.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          <div className="text-4xl mb-3">📊</div>
          <div>No ranked signals for today yet.</div>
          <div className="text-xs mt-1">Signals are generated after market close. Make sure signals have a composite score.</div>
        </div>
      )}

      {!loading && recs.length > 0 && (
        <div className="flex flex-col gap-4">
          {recs.map((rec, i) => (
            <RankedCard key={rec.id} rank={i + 1} rec={rec} />
          ))}
        </div>
      )}
    </div>
  )
}
