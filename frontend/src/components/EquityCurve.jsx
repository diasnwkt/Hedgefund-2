import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

const fmt = (v) => `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`

export default function EquityCurve({ points = [], benchmark = [] }) {
  const combined = points.map((p, i) => ({
    date: new Date(p.timestamp).toLocaleDateString(),
    equity: parseFloat(p.total_equity),
    benchmark: benchmark[i] ? parseFloat(benchmark[i].total_equity) : undefined,
  }))

  return (
    <div className="bg-gray-900 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-gray-400 mb-3">Equity Curve</h2>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={combined} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 11 }} tickLine={false} />
          <YAxis tickFormatter={fmt} tick={{ fill: '#9ca3af', fontSize: 11 }} tickLine={false} width={80} />
          <Tooltip
            contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
            formatter={(v) => fmt(v)}
          />
          <Legend />
          <Line type="monotone" dataKey="equity" stroke="#38bdf8" dot={false} strokeWidth={2} name="Portfolio" />
          <Line type="monotone" dataKey="benchmark" stroke="#6b7280" dot={false} strokeWidth={1.5} strokeDasharray="4 2" name="SPY" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
