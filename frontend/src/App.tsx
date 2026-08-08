import { useEffect, useState } from 'react'
import LoginPage from './pages/LoginPage'
import DailyReportPage from './pages/DailyReportPage'
import { supabase } from './lib/supabaseClient'
import './App.css'

type SessionUser = {
  email?: string
}

function App() {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [checkingSession, setCheckingSession] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session?.user ? { email: data.session.user.email ?? undefined } : null)
      setCheckingSession(false)
    })

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ? { email: session.user.email ?? undefined } : null)
    })

    return () => subscription.subscription.unsubscribe()
  }, [])

  if (checkingSession) {
    return null
  }

  if (user) {
    return (
      <DailyReportPage
        userEmail={user.email}
        onSignOut={() => {
          void supabase.auth.signOut()
        }}
      />
    )
  }

  return <LoginPage onLoginSuccess={(nextUser) => setUser(nextUser)} />
}

export default App
