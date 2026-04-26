const COLORS = { BUY: 'text-green-400 bg-green-900/40', SELL: 'text-red-400 bg-red-900/40', HOLD: 'text-yellow-400 bg-yellow-900/30' }

export default function SignalCard({ signal }) {
  const cls = COLORS[signal.signal] || 'text-gray-400 bg-gray-800'
  const score = signal.composite_score != null ? Number(signal.composite_score) : null

  return (
    <div className="bg-gray-900 rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="font-bold text-white text-base">{signal.symbol}</div>
          <div className="text-xs text-gray-400 mt-0.5">{new Date(signal.generated_at).toLocaleString()}</div>
          <div className="text-xs text-gray-500 mt-0.5">{signal.model_version}</div>
        </div>
        <div className="text-right">
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-bold ${cls}`}>
            {signal.signal}
          </span>
          <div className="text-xs text-gray-400 mt-1">
            {(Number(signal.confidence) * 100).toFixed(1)}% confidence
          </div>
          {signal.executed && (
            <div className="text-xs text-sky-400 mt-0.5">Executed</div>
          )}
        </div>
      </div>
      {score != null && (
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Composite score</span>
            <span>{(score * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-800 rounded-full h-1.5">
            <div
              className="bg-sky-500 h-1.5 rounded-full transition-all"
              style={{ width: `${(score * 100).toFixed(1)}%` }}
            />
          </div>
        </div>
      )}
      {signal.rationale && (
        <div className="text-xs text-gray-400 italic border-t border-gray-800 pt-2">
          {signal.rationale}
        </div>
      )}
    </div>
  )
}
