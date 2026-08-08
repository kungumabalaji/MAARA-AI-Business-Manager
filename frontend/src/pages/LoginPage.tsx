import { useState } from 'react'
import type { FormEvent } from 'react'
import { supabase } from '../lib/supabaseClient'

type LoginPageProps = {
  onLoginSuccess: (user: { email?: string }) => void
}

function LightningIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true">
      <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" />
    </svg>
  )
}

function EnvelopeIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  )
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  )
}

function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const [mode, setMode] = useState<'closed' | 'email'>('closed')
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  function switchAuthMode(nextMode: 'signin' | 'signup') {
    setAuthMode(nextMode)
    setError(null)
    setSuccess(null)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      if (authMode === 'signup') {
        const { data, error: authError } = await supabase.auth.signUp({ email, password })

        if (authError) {
          throw new Error(authError.message)
        }

        if (!data.session) {
          // Email confirmation is required before this account can sign in.
          setSuccess(`Almost there — we've sent a confirmation link to ${email}. Click it, then sign in below.`)
          setAuthMode('signin')
          setPassword('')
          return
        }

        setSuccess('Account created. Your session is ready.')
        setTimeout(() => {
          onLoginSuccess({ email: data.user?.email })
        }, 250)
        setEmail('')
        setPassword('')
        return
      }

      const { data, error: authError } = await supabase.auth.signInWithPassword({ email, password })

      if (authError) {
        throw new Error(authError.message)
      }

      setSuccess(`Welcome back${data.user?.email ? `, ${data.user.email}` : ''}. Your session is ready.`)
      setTimeout(() => {
        onLoginSuccess({ email: data.user?.email })
      }, 250)
      setEmail('')
      setPassword('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error occurred.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-ambient" />
      <div className="login-grid" />

      <header className="topbar">
        <button type="button" className="locale-button">
          <span className="locale-icon" aria-hidden="true" />
          <span>English</span>
          <span className="locale-caret" aria-hidden="true" />
        </button>
      </header>

      <main className="login-layout">
        <section className="hero-panel">
          <div className="left-content">
            <div className="brand-row">
              <img className="brand-mark" src="/logo-mark.png" alt="MAARA" />
              <div>
                <p className="wordmark">MAARA</p>
                <p className="eyebrow">AI Business Management Platform</p>
              </div>
            </div>

            <div className="hero-copy-block">
              <h1>Powering the future of business management.</h1>
              <p className="hero-copy">Intelligence. Automation. Growth.</p>
            </div>

            <div className="hero-security">
              <div className="security-badge" aria-hidden="true">
                <span className="security-shield" />
              </div>
              <div>
                <strong>Enterprise-grade security</strong>
                <p>Built for scale. Designed for trust.</p>
              </div>
            </div>

            <div className="hero-decoration" aria-hidden="true">
              <div className="hero-ribbon-orbit hero-ribbon-orbit-one" />
              <div className="hero-ribbon-orbit hero-ribbon-orbit-two" />
              <img className="hero-logo" src="/maraxdosanchutney.png" alt="mara X Dosa n Chutney" />
              <div className="hero-floor-glow" />
            </div>
          </div>
        </section>

        <section className="auth-panel">
          <div className="auth-card">
            <img className="auth-logo" src="/logo-mark.png" alt="MAARA" />
            <h2>Welcome to MAARA</h2>
            <p className="auth-subtitle">
              {mode === 'email' && authMode === 'signup' ? 'Create an account to get started' : 'Sign in to access your workspace'}
            </p>

            {mode === 'closed' ? (
              <div className="auth-actions">
                <button type="button" className="primary-cta" onClick={() => setMode('email')}>
                  <LightningIcon />
                  <span>Continue with Supabase</span>
                </button>

                <div className="or-row">
                  <span />
                  <p>Secure sign in</p>
                  <span />
                </div>

                <button type="button" className="provider-cta email-cta" onClick={() => setMode('email')}>
                  <EnvelopeIcon />
                  <span>Continue with Email</span>
                </button>
              </div>
            ) : (
              <form className="login-form" onSubmit={handleSubmit}>
                <button type="button" className="auth-back-link" onClick={() => setMode('closed')}>
                  ← Back
                </button>

                <label className="field">
                  <span>Email address</span>
                  <input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@company.com"
                    required
                  />
                </label>

                <label className="field">
                  <span>Password</span>
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder={authMode === 'signup' ? 'Create a password (min. 6 characters)' : 'Enter your password'}
                    minLength={6}
                    required
                  />
                </label>

                {error ? <p className="feedback error">{error}</p> : null}
                {success ? <p className="feedback success">{success}</p> : null}

                <button type="submit" className="primary-cta" disabled={loading}>
                  {loading
                    ? authMode === 'signup'
                      ? 'Creating account...'
                      : 'Signing in...'
                    : authMode === 'signup'
                      ? 'Create Account'
                      : 'Sign In'}
                </button>

                <button
                  type="button"
                  className="auth-toggle-link"
                  onClick={() => switchAuthMode(authMode === 'signup' ? 'signin' : 'signup')}
                >
                  {authMode === 'signup' ? 'Already have an account? Sign in' : "New to MAARA? Create an account"}
                </button>
              </form>
            )}

            <div className="auth-footer-note">
              <span className="auth-footer-badge" aria-hidden="true">
                <LockIcon />
              </span>
              <p>Secure authentication</p>
              <p className="auth-footer-powered">
                Powered by <span>Supabase</span>
              </p>
            </div>
          </div>

          <footer className="page-footer">
            <nav>
              <a href="#privacy">Privacy Policy</a>
              <a href="#terms">Terms of Service</a>
              <a href="#security">Security</a>
            </nav>
            <p>© 2026 MAARA AI. All rights reserved.</p>
          </footer>
        </section>
      </main>
    </div>
  )
}

export default LoginPage