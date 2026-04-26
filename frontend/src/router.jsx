import { createBrowserRouter } from 'react-router-dom'
import React, { Suspense } from 'react'
import { AuthGuard } from './App'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Portfolio from './pages/Portfolio'
import Signals from './pages/Signals'
import Risk from './pages/Risk'
import Settings from './pages/Settings'

const Recommendations = React.lazy(() => import('./pages/Recommendations'))

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    element: <AuthGuard />,
    children: [
      { path: '/', element: <Dashboard /> },
      { path: '/portfolio', element: <Portfolio /> },
      { path: '/signals', element: <Signals /> },
      {
        path: '/recommendations',
        element: (
          <Suspense fallback={<div className="flex justify-center py-16"><div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" /></div>}>
            <Recommendations />
          </Suspense>
        ),
      },
      { path: '/risk', element: <Risk /> },
      { path: '/settings', element: <Settings /> },
    ],
  },
])
