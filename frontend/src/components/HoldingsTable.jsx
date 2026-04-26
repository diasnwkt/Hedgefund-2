const pct = (v) => (v != null ? `${Number(v).toFixed(2)}%` : '—')
const usd = (v) => (v != null ? `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—')

export default function HoldingsTable({ positions = [] }) {
  if (!positions.length) {
    return (
      <div className="bg-gray-900 rounded-xl p-4 text-gray-500 text-sm">
        No open positions.
      </div>
    )
  }

  return (
    <div className="bg-gray-900 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400 text-xs border-b border-gray-800">
            {['Symbol', 'Shares', 'Avg Cost', 'Current', 'Market Value', 'Unrealized P&L', 'P&L %'].map((h) => (
              <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map((pos) => {
            const pnlColor = pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
            return (
              <tr key={pos.id} className="border-b border-gray-800 hover:bg-gray-800/40 transition-colors">
                <td className="px-4 py-3 font-semibold text-white">{pos.symbol}</td>
                <td className="px-4 py-3 text-gray-300">{Number(pos.shares).toFixed(4)}</td>
                <td className="px-4 py-3 text-gray-300">{usd(pos.avg_cost)}</td>
                <td className="px-4 py-3 text-gray-300">{usd(pos.current_price)}</td>
                <td className="px-4 py-3 text-gray-300">{usd(pos.market_value)}</td>
                <td className={`px-4 py-3 font-medium ${pnlColor}`}>{usd(pos.unrealized_pnl)}</td>
                <td className={`px-4 py-3 font-medium ${pnlColor}`}>{pct(pos.unrealized_pnl_pct)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
