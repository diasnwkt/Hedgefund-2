import { useState, useCallback } from 'react'
import { login as apiLogin } from '../api/endpoints'

export function useAuth() {
  const [token, setToken] = useState(() => localStorage.getItem('token'))

  const loginFn = useCallback(async (username, password) => {
    const resp = await apiLogin(username, password)
    const t = resp.data.access_token
    localStorage.setItem('token', t)
    setToken(t)
    return t
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setToken(null)
  }, [])

  return { token, login: loginFn, logout, isAuthenticated: !!token }
}
