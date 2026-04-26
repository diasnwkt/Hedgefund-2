function Metric({ label, value, danger }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className={`text-lg font-bold ${danger ? 'text-red-400' : 'text-white'}`}>
        {value != null ? String(value) : '—'}
      </div>
    </div>
  )
}

export default function RiskGauge({ metrics }) {
  if (!metrics) return null
  const dd = parseFloat(metrics.max_drawdown_pct)
  const ddDanger = !isNaN(dd) && dd < -15

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Metric label="Sharpe Ratio" value={metrics.sharpe_ratio != null ? Number(metrics.sharpe_ratio).toFixed(3) : null} />
      <Metric label="Sortino Ratio" value={metrics.sortino_ratio != null ? Number(metrics.sortino_ratio).toFixed(3) : null} />
      <Metric label="Max Drawdown" value={metrics.max_drawdown_pct != null ? `${Number(metrics.max_drawdown_pct).toFixed(2)}%` : null} danger={ddDanger} />
      <Metric label="VaR (95%)" value={metrics.var_95 != null ? `${(Number(metrics.var_95) * 100).toFixed(2)}%` : null} />
      <Metric label="Beta" value={metrics.beta != null ? Number(metrics.beta).toFixed(3) : null} />
      <Metric label="CAGR" value={metrics.cagr != null ? `${(Number(metrics.cagr) * 100).toFixed(2)}%` : null} />
      <Metric label="Calmar" value={metrics.calmar_ratio != null ? Number(metrics.calmar_ratio).toFixed(3) : null} />
      <Metric label="Total Return" value={metrics.total_return_pct != null ? `${Number(metrics.total_return_pct).toFixed(2)}%` : null} />
    </div>
  )
}
