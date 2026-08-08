import { useState } from 'react'
import LoginPage from './pages/LoginPage'
import DailyReportPage from './pages/DailyReportPage'
import './App.css'

type SessionUser = {
  email?: string
}

function App() {
  const [user, setUser] = useState<SessionUser | null>(null)

  if (user) {
    return <DailyReportPage userEmail={user.email} onSignOut={() => setUser(null)} />
  }

  return <LoginPage onLoginSuccess={(nextUser) => setUser(nextUser)} />
}

export default App
