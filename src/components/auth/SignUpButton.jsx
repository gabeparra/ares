import React from 'react'
import { useAuth0 } from '@auth0/auth0-react'

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
      className="group relative overflow-hidden px-4 py-1.5 border border-white/15 rounded-lg cursor-pointer text-xs font-semibold transition-all duration-300 tracking-wide bg-gradient-to-br from-white/8 to-white/4 text-white backdrop-blur-md shadow-[0_4px_16px_rgba(0,0,0,0.2)] hover:from-white/12 hover:to-white/8 hover:border-white/25 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(0,0,0,0.3)] active:scale-95"
      onClick={handleSignUp}
    >
      <span className="relative z-10 flex items-center gap-1.5">
        <span className="text-sm transition-transform duration-300 group-hover:rotate-12 group-hover:scale-110">✨</span>
        <span>Sign Up</span>
      </span>
      <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
    </button>
  )
}

export default SignUpButton

