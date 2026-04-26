import { useState, useEffect } from 'react'
import { getKillSwitch, setKillSwitch } from '../api/endpoints'

export default function KillSwitch() {
  const [state, setState] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getKillSwitch().then((r) => setState(r.data)).catch(() => {})
  }, [])

  const toggle = async () => {
    const newActive = !state?.active
    const reason = newActive
      ? prompt('Reason for activating kill-switch:') || 'Manual activation'
      : prompt('Reason for deactivating kill-switch:') || 'Manual reset'
    setLoading(true)
    try {
      const r = await setKillSwitch(newActive, reason)
      setState(r.data)
    } finally {
      setLoading(false)
    }
  }

  const active = state?.active
  return (
    <button
      onClick={toggle}
      disabled={loading}
      title={active ? `Kill-switch ACTIVE: ${state?.reason}` : 'Kill-switch inactive'}
      className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
        active
          ? 'bg-red-600 text-white hover:bg-red-700 ring-2 ring-red-400'
          : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
      }`}
    >
      {active ? 'KILL-SWITCH ON' : 'Kill-Switch'}
    </button>
  )
}
