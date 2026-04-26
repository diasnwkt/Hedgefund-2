export default function ModeIndicator({ mode }) {
  const isLive = mode === 'live'
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
        isLive ? 'bg-red-600 text-white animate-pulse' : 'bg-green-800 text-green-200'
      }`}
    >
      <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-red-200' : 'bg-green-400'}`} />
      {isLive ? 'LIVE' : 'PAPER'}
    </span>
  )
}
