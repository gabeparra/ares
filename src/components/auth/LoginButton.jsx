import React from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import './Auth.css'

function LoginButton() {
  const { loginWithRedirect, isAuthenticated } = useAuth0()

  if (isAuthenticated) {
    return null
  }

  return (
    <button 
      className="auth-button login-button"
      onClick={() => loginWithRedirect()}
    >
      Log In
    </button>
  )
}

export default LoginButton

