import React from 'react'
import { useAuth0 } from '@auth0/auth0-react'
import './Auth.css'

function SignUpButton() {
  const { loginWithRedirect, isAuthenticated } = useAuth0()

  if (isAuthenticated) {
    return null
  }

  const handleSignUp = () => {
    loginWithRedirect({
      authorizationParams: {
        screen_hint: 'signup'
      }
    })
  }

  return (
    <button 
      className="auth-button signup-button"
      onClick={handleSignUp}
    >
      Sign Up
    </button>
  )
}

export default SignUpButton

