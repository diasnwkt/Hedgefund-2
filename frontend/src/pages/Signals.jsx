import { useState } from 'react'
import { usePolling } from '../hooks/usePolling'
import { getSignalsHistory } from '../api/endpoints'
import SignalCard from '../components/SignalCard'

const POLL = parseInt(import.meta.env.VITE_POLLING_INTERVAL_MS || '60000')

export default function Signals() {
  const [filter, setFilter] = useState('')
  const { data: signals } = usePolling(getSignalsHistory, POLL)

  const filtered = (signals || []).filter(
    (s) => !filter || s.signal === filter || s.symbol.includes(filter.toUpperCase())
  )

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {['', 'BUY', 'SELL', 'HOLD'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filter === f ? 'bg-sky-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {f || 'All'}
          </button>
        ))}
      </div>

      {filtered.length ? (
        <div className="grid md:grid-cols-2 gap-3">
          {filtered.map((s) => <SignalCard key={s.id} signal={s} />)}
        </div>
      ) : (
        <div className="text-gray-500 text-sm">No signals found.</div>
      )}
    </div>
  )
}
