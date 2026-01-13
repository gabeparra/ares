import React from 'react'
import { useAuth0 } from '@auth0/auth0-react'

function LoginButton() {
  const { loginWithRedirect, isAuthenticated } = useAuth0()

  if (isAuthenticated) {
    return null
  }

  return (
    <button
      className="group relative overflow-hidden px-4 py-1.5 border-none rounded-lg cursor-pointer text-xs font-semibold transition-all duration-300 tracking-wide bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-[0_4px_16px_rgba(59,130,246,0.3)] hover:from-blue-400 hover:to-blue-500 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(59,130,246,0.4)] active:scale-95"
      onClick={() => loginWithRedirect()}
    >
      <span className="relative z-10 flex items-center gap-1.5">
        <span>Log In</span>
        <span className="text-sm transition-transform duration-300 group-hover:translate-x-0.5">→</span>
      </span>
      <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
    </button>
  )
}

export default LoginButton

