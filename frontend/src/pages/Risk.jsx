import { usePolling } from '../hooks/usePolling'
import { getRiskMetrics, getKillSwitch, setKillSwitch, getAuditLog } from '../api/endpoints'
import RiskGauge from '../components/RiskGauge'

const POLL = parseInt(import.meta.env.VITE_POLLING_INTERVAL_MS || '60000')

export default function Risk() {
  const { data: metrics } = usePolling(getRiskMetrics, POLL)
  const { data: ks, refresh: refreshKs } = usePolling(getKillSwitch, POLL)
  const { data: audit } = usePolling(getAuditLog, POLL)

  const toggleKs = async () => {
    const newActive = !ks?.active
    const reason = prompt(newActive ? 'Reason for activating:' : 'Reason for deactivating:') || 'Manual'
    await setKillSwitch(newActive, reason)
    refreshKs()
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-sm font-semibold text-gray-400 mb-3">Risk Metrics (365 days)</h2>
        <RiskGauge metrics={metrics} />
      </div>

      <div className="bg-gray-900 rounded-xl p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-gray-400">Kill-Switch</h2>
            {ks?.active && (
              <p className="text-red-400 text-xs mt-1">Active: {ks.reason}</p>
            )}
            {ks?.activated_at && (
              <p className="text-gray-500 text-xs">{new Date(ks.activated_at).toLocaleString()}</p>
            )}
          </div>
          <button
            onClick={toggleKs}
            className={`px-4 py-2 rounded-lg text-sm font-bold transition-colors ${
              ks?.active ? 'bg-red-600 hover:bg-red-700 text-white' : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
            }`}
          >
            {ks?.active ? 'DEACTIVATE' : 'Activate'}
          </button>
        </div>
      </div>

      {audit?.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 mb-3">Recent Audit Log</h2>
          <div className="space-y-2">
            {audit.slice(0, 20).map((entry) => (
              <div key={entry.id} className="bg-gray-900 rounded-lg px-4 py-2 text-xs flex gap-4">
                <span className="text-gray-500 w-40 shrink-0">{new Date(entry.timestamp).toLocaleString()}</span>
                <span className="text-sky-400 w-28 shrink-0">{entry.event_type}</span>
                <span className="text-gray-400 w-16 shrink-0">{entry.actor}</span>
                <span className="text-gray-300 truncate">{JSON.stringify(entry.details)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
