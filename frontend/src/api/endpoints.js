import client from './client'

export const login = (username, password) => {
  const form = new FormData()
  form.append('username', username)
  form.append('password', password)
  return client.post('/auth/login', form)
}

export const getHealth = () => client.get('/health')
export const getPortfolioSummary = () => client.get('/portfolio/summary')
export const getPositions = () => client.get('/portfolio/positions')
export const getPositionHistory = () => client.get('/portfolio/history')
export const getEquityHistory = (days = 90) => client.get(`/portfolio/equity/history?days=${days}`)
export const getBenchmark = (days = 90) => client.get(`/portfolio/equity/benchmark?days=${days}`)

export const getSignalsToday = () => client.get('/signals/today')
export const getSignalsHistory = (limit = 100) => client.get(`/signals/history?limit=${limit}`)
export const getRankedSignals = (limit = 20) => client.get(`/signals/ranked?limit=${limit}`)

export const getRiskMetrics = () => client.get('/risk/metrics')
export const getKillSwitch = () => client.get('/risk/killswitch')
export const setKillSwitch = (active, reason) => client.post('/risk/killswitch', { active, reason })

export const getWatchlist = () => client.get('/settings/watchlist')
export const updateWatchlist = (symbols) => client.post('/settings/watchlist', { symbols })
export const getMode = () => client.get('/settings/mode')
export const setMode = (mode, confirm) => client.post('/settings/mode', { mode, confirm })
export const getAuditLog = (event_type) => client.get(`/settings/audit/log${event_type ? `?event_type=${event_type}` : ''}`)
