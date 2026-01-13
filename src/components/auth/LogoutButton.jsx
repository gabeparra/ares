import React from 'react'
import { useAuth0 } from '@auth0/auth0-react'

function LogoutButton() {
  const { logout, isAuthenticated, user } = useAuth0()

  if (!isAuthenticated) {
    return null
  }

  return (
    <div className="flex items-center gap-2">
      {/* User Profile Card */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-white/6 border border-white/12 rounded-xl backdrop-blur-md transition-all duration-300 hover:bg-white/8 hover:border-white/18 hover:shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
        {user?.picture && (
          <img
            src={user.picture}
            alt={user.name || user.email}
            className="w-7 h-7 rounded-full border-2 border-red-500/40 shadow-[0_0_12px_rgba(255,0,0,0.3)] transition-all duration-300 hover:border-red-500/60 hover:scale-105"
          />
        )}
        <div className="flex flex-col gap-0 hidden sm:flex">
          <span className="text-white text-xs font-semibold tracking-wide leading-tight">
            {user?.name || user?.email || 'User'}
          </span>
          {user?.email && user?.name && (
            <span className="text-white/40 text-0.7em font-mono truncate max-w-32" title={user.email}>
              {user.email}
            </span>
          )}
        </div>
      </div>
      
      {/* Logout Button */}
      <button
        className="group relative overflow-hidden px-4 py-1.5 border-none rounded-xl cursor-pointer text-xs font-semibold transition-all duration-300 tracking-wide bg-gradient-to-br from-red-500/80 to-red-600/80 text-white shadow-[0_4px_16px_rgba(255,0,0,0.25)] hover:from-red-500 hover:to-red-600 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(255,0,0,0.35)] active:scale-95"
        onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
      >
        <span className="relative z-10 flex items-center gap-2">
          <span>Log Out</span>
          <span className="text-base transition-transform duration-300 group-hover:translate-x-0.5">→</span>
        </span>
        <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
      </button>
    </div>
  )
}

export default LogoutButton

