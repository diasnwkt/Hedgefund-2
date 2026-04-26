import { useState, useEffect, useRef, useCallback } from 'react'

export function usePolling(fetchFn, intervalMs = 60000, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const timerRef = useRef(null)

  const fetch = useCallback(async () => {
    try {
      setError(null)
      const result = await fetchFn()
      setData(result.data)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => {
    fetch()
    timerRef.current = setInterval(fetch, intervalMs)
    return () => clearInterval(timerRef.current)
  }, [fetch, intervalMs])

  return { data, loading, error, refresh: fetch }
}
