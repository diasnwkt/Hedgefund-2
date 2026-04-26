import { usePolling } from '../hooks/usePolling'
import { getPortfolioSummary, getEquityHistory, getBenchmark, getSignalsToday } from '../api/endpoints'
import EquityCurve from '../components/EquityCurve'
import SignalCard from '../components/SignalCard'

const usd = (v) => `$${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
const pct = (v) => `${Number(v).toFixed(2)}%`

function StatCard({ label, value, sub, color }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color || 'text-white'}`}>{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  )
}

const POLL = parseInt(import.meta.env.VITE_POLLING_INTERVAL_MS || '60000')

export default function Dashboard() {
  const { data: summary } = usePolling(getPortfolioSummary, POLL)
  const { data: equity } = usePolling(getEquityHistory, POLL)
  const { data: bench } = usePolling(getBenchmark, POLL)
  const { data: signals } = usePolling(getSignalsToday, POLL)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Equity" value={summary ? usd(summary.total_equity) : '—'} />
        <StatCard
          label="Total Return"
          value={summary ? pct(summary.total_return_pct) : '—'}
          color={summary && summary.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}
        />
        <StatCard label="Cash" value={summary ? usd(summary.cash) : '—'} />
        <StatCard
          label="Drawdown"
          value={summary ? pct(summary.current_drawdown_pct) : '—'}
          color={summary && summary.current_drawdown_pct < -10 ? 'text-red-400' : 'text-gray-200'}
          sub="from peak"
        />
      </div>

      <EquityCurve points={equity?.points || []} benchmark={bench?.points || []} />

      <div>
        <h2 className="text-sm font-semibold text-gray-400 mb-3">
          Today's Signals
          {signals && (
            <span className="ml-2 text-gray-500">
              ({signals.generated_count} generated, {signals.executed_count} executed)
            </span>
          )}
        </h2>
        {signals?.signals?.length ? (
          <div className="grid md:grid-cols-2 gap-3">
            {signals.signals.map((s) => <SignalCard key={s.id} signal={s} />)}
          </div>
        ) : (
          <div className="text-gray-500 text-sm">No signals generated today.</div>
        )}
      </div>
    </div>
  )
}
