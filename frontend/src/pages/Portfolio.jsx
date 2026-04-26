import { usePolling } from '../hooks/usePolling'
import { getPositions, getPositionHistory, getPortfolioSummary } from '../api/endpoints'
import HoldingsTable from '../components/HoldingsTable'

const usd = (v) => `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
const pct = (v) => `${Number(v).toFixed(2)}%`
const POLL = parseInt(import.meta.env.VITE_POLLING_INTERVAL_MS || '60000')

export default function Portfolio() {
  const { data: positions } = usePolling(getPositions, POLL)
  const { data: history } = usePolling(getPositionHistory, POLL)
  const { data: summary } = usePolling(getPortfolioSummary, POLL)

  return (
    <div className="space-y-6">
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Cash', value: usd(summary.cash) },
            { label: 'Positions Value', value: usd(summary.positions_value) },
            { label: 'Realized P&L', value: usd(summary.realized_pnl), color: summary.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400' },
            { label: 'Unrealized P&L', value: usd(summary.unrealized_pnl), color: summary.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-900 rounded-xl p-4">
              <div className="text-xs text-gray-400 mb-1">{label}</div>
              <div className={`text-xl font-bold ${color || 'text-white'}`}>{value}</div>
            </div>
          ))}
        </div>
      )}

      <div>
        <h2 className="text-sm font-semibold text-gray-400 mb-3">Open Positions</h2>
        <HoldingsTable positions={positions || []} />
      </div>

      {history?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-3">Closed Positions</h2>
          <div className="bg-gray-900 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 text-xs border-b border-gray-800">
                  {['Symbol', 'Shares', 'Avg Cost', 'Realized P&L', 'Opened', 'Closed'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {history.map((pos) => (
                  <tr key={pos.id} className="border-b border-gray-800">
                    <td className="px-4 py-2 font-semibold text-white">{pos.symbol}</td>
                    <td className="px-4 py-2 text-gray-300">{Number(pos.shares).toFixed(4)}</td>
                    <td className="px-4 py-2 text-gray-300">{usd(pos.avg_cost)}</td>
                    <td className={`px-4 py-2 font-medium ${pos.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {usd(pos.realized_pnl)}
                    </td>
                    <td className="px-4 py-2 text-gray-400 text-xs">{new Date(pos.opened_at).toLocaleDateString()}</td>
                    <td className="px-4 py-2 text-gray-400 text-xs">{pos.closed_at ? new Date(pos.closed_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
