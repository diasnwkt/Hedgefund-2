import { useEffect, useState } from 'react'
import { Navigate, Outlet, useNavigate } from 'react-router-dom'
import Layout from './components/Layout'
import { getMode } from './api/endpoints'

export function AuthGuard() {
  const token = localStorage.getItem('token')
  const navigate = useNavigate()
  const [mode, setMode] = useState(null)

  useEffect(() => {
    if (!token) {
      navigate('/login', { replace: true })
      return
    }
    getMode().then((r) => setMode(r.data.mode)).catch(() => {})
  }, [token])

  if (!token) return <Navigate to="/login" replace />

  return (
    <Layout mode={mode}>
      <Outlet />
    </Layout>
  )
}
