import { useAuth0 } from "@auth0/auth0-react";
import { useEffect, useState } from "react";
import { Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import LoginButton from "./components/auth/LoginButton";
import SignUpButton from "./components/auth/SignUpButton";
import LogoutButton from "./components/auth/LogoutButton";
import DevLoginButton from "./components/auth/DevLoginButton";
import ChatPanel from "./components/chat/ChatPanel";
import DemoChat from "./components/chat/DemoChat";
import ConversationList from "./components/conversations/ConversationList";
import ConnectionStatus from "./components/controls/ConnectionStatus";
import TelegramStatus from "./components/controls/TelegramStatus";
import DiscordStatusCompact from "./components/controls/DiscordStatusCompact";
import ProviderSelector from "./components/controls/ProviderSelector";
import TranscriptUpload from "./components/transcripts/TranscriptUpload";
import ModelSettings from "./components/settings/ModelSettings";
import LogsPanel from "./components/logs/LogsPanel";
import SDApiPanel from "./components/api/SDApiPanel";
import OllamaApiPanel from "./components/api/OllamaApiPanel";
import IdentityPanel from "./components/identity/IdentityPanel";
import UserMemoryPanel from "./components/memory/UserMemoryPanel";
import AgentPanel from "./components/agent/AgentPanel";
import CalendarPanel from "./components/calendar/CalendarPanel";
import CodeBrowser from "./components/code/CodeBrowser";
import UserManagerPanel from "./components/users/UserManagerPanel";
import ToolsPanel from "./components/tools/ToolsPanel";
import Tabs from "./components/Tabs";
import TabPanel from "./components/TabPanel";
import { apiGet } from "./services/api";
import { setAuthToken, clearAuthToken, setRefreshTokenCallback, clearAuthModule, checkDevAdminToken, clearDevAdminAuth } from "./services/auth";
import useUIStore from "./stores/uiStore";
import { useTabVisibility } from "./hooks/useTabVisibility";

function App() {
  const {
    isAuthenticated,
    isLoading,
    error,
    getAccessTokenSilently,
    user,
    getIdTokenClaims,
    loginWithRedirect,
  } = useAuth0();
  const [hasAccess, setHasAccess] = useState(false);
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [accessDebugInfo, setAccessDebugInfo] = useState(null);
  
  // Dev admin state
  const [devAdminAuth, setDevAdminAuth] = useState(null);
  
  // Check for dev admin token on mount
  useEffect(() => {
    const devAuth = checkDevAdminToken();
    if (devAuth) {
      console.log('Dev admin token found:', devAuth.user?.email);
      setDevAdminAuth(devAuth);
      setHasAccess(true);
      setCheckingAccess(false);
    }
  }, []);

  // Listen for authentication failures from API calls
  useEffect(() => {
    const handleAuthRequired = (event) => {
      console.log('Authentication required event received:', event.detail);
      if (isAuthenticated && !isRedirecting) {
        // User is authenticated but token refresh failed - force re-login
        console.log('Forcing re-login due to authentication failure...');
        setIsRedirecting(true);
        loginWithRedirect({
          authorizationParams: {
            prompt: 'login'
          }
        }).catch((err) => {
          console.error('Failed to redirect to login:', err);
          setIsRedirecting(false);
        });
      }
    };

    window.addEventListener('ares:auth-required', handleAuthRequired);

    return () => {
      window.removeEventListener('ares:auth-required', handleAuthRequired);
    };
  }, [isAuthenticated, loginWithRedirect, isRedirecting]);

  // SECURITY: Store auth token securely in memory (not in window object)
  useEffect(() => {
    if (isAuthenticated) {
      const refreshToken = async () => {
        try {
          // Force Auth0 to refresh the session by getting a fresh access token first
          // This ensures the session is restored if the user comes back after closing browser
          try {
            await getAccessTokenSilently({
              cacheMode: 'off',
              authorizationParams: {
                prompt: 'none' // Silent refresh, don't show login prompt
              }
            });
          } catch (e) {
            // If silent refresh fails, the session might be expired
            console.warn("Silent token refresh failed, will try ID token:", e);
          }

          // Get ID token claims - Auth0 SDK should handle refresh automatically
          // If the session is valid, this will get a fresh token
          const claims = await getIdTokenClaims();
          if (!claims || !claims.__raw) {
            throw new Error("Failed to get ID token claims");
          }

          // SECURITY: Store in secure memory module instead of window object
          setAuthToken(claims.__raw);

          // Don't trigger access check here - it causes circular loops
          // Access check will use the refreshed token automatically via apiGet

          return claims.__raw;
        } catch (err) {
          console.error("Failed to refresh token:", err);
          clearAuthToken();
          
          // If token refresh fails, trigger re-login
          // Check if this is a session expiration error
          const errorMessage = err?.message || String(err);
          if (errorMessage.includes('login_required') || 
              errorMessage.includes('consent_required') ||
              errorMessage.includes('interaction_required') ||
              errorMessage.includes('Failed to get ID token claims')) {
            console.log("Session expired, redirecting to login...");
            // Dispatch event to trigger re-login (will be handled by event listener)
            // This prevents double redirects if both refreshToken and api.js trigger it
            window.dispatchEvent(new CustomEvent('ares:auth-required', {
              detail: { reason: 'Token refresh failed', source: 'refreshToken' }
            }));
          }
          
          throw err;
        }
      };

      // Initial token fetch
      refreshToken().catch((err) => {
        console.error("Initial token fetch failed:", err);
      });

      // SECURITY: Set up refresh callback in secure auth module
      setRefreshTokenCallback(refreshToken);

      // Set up periodic token refresh (every 30 minutes to keep token fresh)
      // Auth0 ID tokens typically expire after 1 hour
      // Note: This won't trigger access check to avoid loops
      const refreshInterval = setInterval(() => {
        if (isAuthenticated) {
          refreshToken().catch((err) => {
            console.error("Periodic token refresh failed:", err);
          });
        }
      }, 30 * 60 * 1000); // 30 minutes

      return () => {
        clearInterval(refreshInterval);
        clearAuthModule();
      };
    } else {
      // Clear auth when not authenticated
      clearAuthModule();
    }
  }, [isAuthenticated, getIdTokenClaims, getAccessTokenSilently, loginWithRedirect]);

  // Check if user has admin role via backend API
  useEffect(() => {
    let isChecking = false;
    let checkTimeout = null;

    const checkAccess = async () => {
      // Prevent multiple simultaneous checks
      if (isChecking) {
        return;
      }

      if (!isAuthenticated || !user) {
        setHasAccess(false);
        setCheckingAccess(false);
        return;
      }

      isChecking = true;
      setCheckingAccess(true);

      // Wait a bit for Auth0 to fully restore the session
      // This is especially important when coming back after closing the browser
      await new Promise(resolve => setTimeout(resolve, 100));

      try {
        // apiGet will handle token refresh automatically if needed
        // No need to manually check - the secure auth module handles this

        // Use apiGet which automatically handles token refresh and retry on 401
        const response = await apiGet("/api/v1/auth/check-admin");

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          console.error(
            "Failed to check admin role:",
            response.status,
            errorData
          );
          setHasAccess(false);
          isChecking = false;
          setCheckingAccess(false);
          return;
        }

        const data = await response.json();
        console.log("Admin role check result:", data);

        if (data.errors && data.errors.length > 0) {
          console.error("Errors checking admin role:", data.errors);
          // Log each error
          data.errors.forEach((err, idx) => {
            console.error(`Error ${idx + 1}:`, err);
          });
        }

        if (data.error) {
          console.error("Error checking admin role:", data.error);
        }

        // Show detailed debug info
        if (data.debug) {
          console.log("Debug info:", data.debug);
        }

        // Store debug info for display
        setAccessDebugInfo({
          has_admin_role: data.has_admin_role,
          errors: data.errors || [],
          debug: data.debug || {},
          user_id: data.user_id,
          email: data.email,
        });

        setHasAccess(data.has_admin_role === true);
      } catch (err) {
        console.error("Failed to check user roles:", err);
        // Don't retry here - apiGet already handles retry with token refresh
        // If it still fails after retry, the token is likely invalid
        setHasAccess(false);
        setAccessDebugInfo({
          has_admin_role: false,
          errors: [err.message || String(err)],
          debug: {},
        });
      } finally {
        isChecking = false;
        setCheckingAccess(false);
      }
    };

    // Set up debounced trigger function for external access check refresh
    // This prevents rapid-fire calls that could cause loops
    window.triggerAccessCheck = () => {
      if (isAuthenticated && user && !isChecking) {
        // Clear any pending check
        if (checkTimeout) {
          clearTimeout(checkTimeout);
        }
        // Debounce: wait 500ms before checking (in case multiple triggers happen)
        checkTimeout = setTimeout(() => {
          checkAccess();
        }, 500);
      }
    };

    checkAccess();

    return () => {
      if (checkTimeout) {
        clearTimeout(checkTimeout);
      }
      window.triggerAccessCheck = null;
    };
  }, [isAuthenticated, user, getIdTokenClaims]);

  if (isLoading || checkingAccess) {
    return (
      <AuthShell>
        <div className="text-dark-text4 text-15px leading-normal py-18px">Loading...</div>
      </AuthShell>
    );
  }

  if (error) {
    return (
      <AuthShell>
        <div className="text-18px font-bold text-red-accent-3 mb-8px">Authentication Error</div>
        <div className="text-dark-text3 text-13px leading-normal mb-14px">{error.message}</div>
        <div className="flex justify-center items-center gap-12px mt-10px flex-wrap">
          <button
            className="auth-button"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </AuthShell>
    );
  }

  // If dev admin is authenticated, show main interface
  if (devAdminAuth) {
    return <MainInterface isDevAdmin={true} devUser={devAdminAuth.user} />;
  }

  if (!isAuthenticated) {
    return <DemoInterface />;
  }

  // Check access - only allow users with admin role
  if (!hasAccess) {
    return (
      <AuthShell>
        <div className="flex flex-col gap-8px">
          <div className="text-32px font-bold tracking-wide text-white">Access denied</div>
          <div className="text-dark-text3 text-14px leading-normal">
            Your account is not authorized for this app.
          </div>
        </div>
        <div className="h-1px w-full bg-gradient-to-r from-transparent via-red-border-3 to-transparent my-18px" />
        <div className="mt-16px text-dark-text3 text-13px leading-normal">
          Signed in as{" "}
          <span className="text-dark-text4 font-mono">{user?.email || "Unknown"}</span>
        </div>
        {accessDebugInfo && (
          <div
            style={{
              marginTop: "20px",
              padding: "15px",
              backgroundColor: "#f5f5f5",
              color: "#1a1a1a",
              borderRadius: "8px",
              fontSize: "0.85em",
              textAlign: "left",
              maxWidth: "600px",
            }}
          >
            <div style={{ fontWeight: "bold", marginBottom: "10px" }}>
              Debug Information:
            </div>
            {accessDebugInfo.errors && accessDebugInfo.errors.length > 0 && (
              <div style={{ marginBottom: "10px" }}>
                <div style={{ fontWeight: "bold", color: "#d32f2f" }}>
                  Errors:
                </div>
                <ul style={{ margin: "5px 0", paddingLeft: "20px" }}>
                  {accessDebugInfo.errors.map((err, idx) => (
                    <li key={idx} style={{ color: "#d32f2f" }}>
                      {err}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {accessDebugInfo.debug && accessDebugInfo.debug.role_check && (
              <div style={{ marginBottom: "10px" }}>
                <div style={{ fontWeight: "bold" }}>Role Check Details:</div>
                <div style={{ marginTop: "5px" }}>
                  <div>
                    User ID: {accessDebugInfo.user_id || "Unknown"}
                  </div>
                  <div>
                    Roles Found: {accessDebugInfo.debug.role_check.roles_found || 0}
                  </div>
                  {accessDebugInfo.debug.role_check.role_names && (
                    <div>
                      Your Roles: {accessDebugInfo.debug.role_check.role_names.join(", ") || "None"}
                    </div>
                  )}
                  {accessDebugInfo.debug.role_check.looking_for_role_id && (
                    <div>
                      Looking for Role ID: {accessDebugInfo.debug.role_check.looking_for_role_id}
                    </div>
                  )}
                  {accessDebugInfo.debug.role_check.error && (
                    <div style={{ color: "#d32f2f", marginTop: "5px" }}>
                      Error: {accessDebugInfo.debug.role_check.error}
                    </div>
                  )}
                </div>
              </div>
            )}
            {accessDebugInfo.debug && Object.keys(accessDebugInfo.debug).length > 0 && (
              <details style={{ marginTop: "10px" }}>
                <summary style={{ cursor: "pointer", fontWeight: "bold" }}>
                  Full Debug Info
                </summary>
                <pre
                  style={{
                    marginTop: "10px",
                    padding: "10px",
                    backgroundColor: "#fff",
                    borderRadius: "4px",
                    overflow: "auto",
                    fontSize: "0.75em",
                  }}
                >
                  {JSON.stringify(accessDebugInfo.debug, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}
        <div className="mt-16px text-dark-text3 text-13px leading-normal text-0.85em mt-10px text-gray-500">
          You need the "admin" role assigned in Auth0 to access this application.
          <br />
          Please check the browser console (F12) for additional details.
        </div>
        <div className="flex justify-center items-center gap-12px mt-10px flex-wrap">
          <LogoutButton />
        </div>
      </AuthShell>
    );
  }

  // Authenticated and authorized - show main ARES interface
  return <MainInterface />;
}

function DemoInterface() {
  return (
    <div className="w-full m-0 p-16px md:p-12px h-screen max-h-screen flex flex-col overflow-hidden box-border">
      <header className="glass-header p-8px md:p-6px mb-6px md:mb-4px flex-shrink-0 animate-fade-in-scale relative z-10 overflow-visible">
        <div className="flex flex-row items-center justify-between w-full gap-8px overflow-visible">
          <div className="flex-1 min-w-0 flex flex-col items-center justify-center gap-2px overflow-visible">
            <h1 className="text-xl md:text-lg lg:text-2xl tracking-tight m-0 leading-none font-bold whitespace-nowrap flex-shrink-0 text-center" style={{
              color: '#e2e8f0',
              textShadow: '0 0 8px rgba(255, 0, 0, 0.25), 0 0 16px rgba(255, 0, 0, 0.12), 0 0 24px rgba(255, 100, 100, 0.08), 0 2px 4px rgba(0, 0, 0, 0.3)'
            }}>
              ARES
            </h1>
            <div className="text-white-opacity-65 text-xs tracking-wide font-medium leading-tight flex-shrink-0 whitespace-nowrap text-center">
              AI Orchestration and Control System
            </div>
          </div>
          <div className="flex items-center gap-4px flex-shrink-0 overflow-visible flex-nowrap">
            <DevLoginButton />
            <LoginButton />
            <SignUpButton />
          </div>
        </div>
      </header>

      <div className="flex flex-col flex-1 min-h-0 max-h-full overflow-hidden animate-fade-in relative z-0">
        <DemoChat />
      </div>
    </div>
  );
}

function MainInterface({ isDevAdmin = false, devUser = null }) {
  const navigate = useNavigate();
  const location = useLocation();
  
  const handleDevLogout = () => {
    clearDevAdminAuth();
    window.location.reload();
  };
  
  // Use Zustand store for UI state
  const {
    activeTab,
    setActiveTab,
    selectedSessionId,
    setSelectedSessionId,
    currentModel,
    setCurrentModel,
    currentProvider,
    setCurrentProvider,
    tabVisibility,
    setTabVisibility,
  } = useUIStore();

  // Sync route with active tab (when route changes externally, e.g., browser back/forward)
  useEffect(() => {
    const path = location.pathname.replace('/', '') || 'chat';
    if (path !== activeTab && path !== '') {
      setActiveTab(path);
    }
  }, [location.pathname, setActiveTab]);

  // Load tab visibility settings using React Query
  const { data: tabVisibilityData } = useTabVisibility();
  
  useEffect(() => {
    if (tabVisibilityData) {
      setTabVisibility(tabVisibilityData);
    }
  }, [tabVisibilityData, setTabVisibility]);

  const allTabs = [
    { id: "chat", label: "Chat", icon: "💬" },
    { id: "code", label: "Code", icon: "🗂️" },
    { id: "agent", label: "Agent", icon: "🤖" },
    { id: "identity", label: "Identity", icon: "🧠" },
    { id: "memory", label: "Memory", icon: "📝" },
    { id: "sessions", label: "Sessions", icon: "📋" },
    { id: "users", label: "Users", icon: "👥" },
    { id: "transcripts", label: "Transcripts", icon: "📄" },
    { id: "calendar", label: "Calendar", icon: "📅" },
    { id: "tools", label: "Tools", icon: "🛠️" },
    { id: "sdapi", label: "SD API", icon: "🎨" },
    { id: "ollama", label: "Ollama", icon: "🦙" },
    { id: "settings", label: "Settings", icon: "⚙️" },
    { id: "logs", label: "Logs", icon: "📊" },
  ];

  // Filter tabs based on visibility settings
  const tabs = allTabs.filter(tab => {
    if (tab.id === "sdapi") {
      return tabVisibility.sdapi !== false; // Show unless explicitly hidden
    }
    return true; // Show all other tabs
  });

  const handleSessionSelect = (sessionId) => {
    setSelectedSessionId(sessionId);
    setActiveTab("chat");
    navigate("/chat");
  };

  const handleModelChange = (model) => {
    setCurrentModel(model);
  };

  const handleProviderChange = (provider) => {
    setCurrentProvider(provider);
  };

  return (
    <div className="w-full m-0 p-16px md:p-10px h-screen max-h-screen flex flex-col overflow-hidden box-border">
      <header className="glass-header p-16px md:p-12px mb-12px md:mb-10px flex-shrink-0 animate-fade-in-scale">
        <div className="flex flex-row items-center justify-between w-full gap-16px">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-8px mt-0 leading-snug whitespace-nowrap">
              <h1 className="text-clamp-1.4em-1.8em tracking-1px m-0 leading-none font-bold md:text-xl text-white" style={{
                textShadow: '0 0 8px rgba(255, 0, 0, 0.5), 0 0 16px rgba(255, 0, 0, 0.3), 0 0 24px rgba(255, 100, 100, 0.2), 0 2px 4px rgba(0, 0, 0, 0.3)'
              }}>
                ARES
              </h1>
              <div className="text-white-opacity-65 text-sm md:text-xs lg:text-base tracking-wide font-medium">
                AI Orchestration and Control System
              </div>
            </div>
          </div>
          <div className="flex items-center gap-8px flex-shrink-0 flex-nowrap">
            <ConnectionStatus />
            <TelegramStatus />
            <DiscordStatusCompact />
            {isDevAdmin ? (
              <div className="flex items-center gap-2 flex-shrink-0">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/20 border border-amber-500/40 rounded-xl flex-shrink-0">
                  <span className="text-amber-400 text-xs">🔧</span>
                  <span className="text-amber-300 text-xs font-medium whitespace-nowrap">{devUser?.email || 'Dev Admin'}</span>
                </div>
                <button
                  onClick={handleDevLogout}
                  className="px-4 py-1.5 bg-gradient-to-r from-amber-500/60 to-orange-500/60 text-white text-xs font-semibold rounded-xl hover:from-amber-500/80 hover:to-orange-500/80 transition-all duration-200 flex-shrink-0 whitespace-nowrap"
                >
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex-shrink-0">
                <LogoutButton />
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="flex flex-col flex-1 min-h-0 h-full max-h-full overflow-hidden animate-fade-in">
        <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab}>
          <Routes>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={
                <TabPanel active={activeTab === "chat"} id="chat">
                  <ChatPanel
                    sessionId={selectedSessionId}
                    onSessionChange={setSelectedSessionId}
                  />
                </TabPanel>
              } />
              <Route path="/code" element={
                <TabPanel active={activeTab === "code"} id="code">
                  <CodeBrowser />
                </TabPanel>
              } />
              <Route path="/agent" element={
                <TabPanel active={activeTab === "agent"} id="agent">
                  <AgentPanel />
                </TabPanel>
              } />
              <Route path="/identity" element={
                <TabPanel active={activeTab === "identity"} id="identity">
                  <IdentityPanel />
                </TabPanel>
              } />
              <Route path="/memory" element={
                <TabPanel active={activeTab === "memory"} id="memory">
                  <UserMemoryPanel />
                </TabPanel>
              } />
              <Route path="/sessions" element={
                <TabPanel active={activeTab === "sessions"} id="sessions">
                  <ConversationList
                    onSelectSession={handleSessionSelect}
                    selectedSessionId={selectedSessionId}
                  />
                </TabPanel>
              } />
              <Route path="/users" element={
                <TabPanel active={activeTab === "users"} id="users">
                  <UserManagerPanel />
                </TabPanel>
              } />
              <Route path="/transcripts" element={
                <TabPanel active={activeTab === "transcripts"} id="transcripts">
                  <TranscriptUpload
                    onSummaryGenerated={(summary, filename) => {
                      console.log("Summary generated:", summary, filename);
                    }}
                  />
                </TabPanel>
              } />
              <Route path="/calendar" element={
                <TabPanel active={activeTab === "calendar"} id="calendar">
                  <CalendarPanel />
                </TabPanel>
              } />
              <Route path="/tools" element={
                <TabPanel active={activeTab === "tools"} id="tools">
                  <ToolsPanel />
                </TabPanel>
              } />
              <Route path="/settings" element={
                <TabPanel active={activeTab === "settings"} id="settings">
                  <div className="panel h-full min-h-0">
                    <ProviderSelector
                      currentProvider={currentProvider}
                      onProviderChange={(provider) => {
                        handleProviderChange(provider)
                        // Trigger model reload when provider changes
                        // The ModelSettings component will detect the provider change via useEffect
                      }}
                    />
                    <ModelSettings
                      currentModel={currentModel}
                      onModelChange={handleModelChange}
                      currentProvider={currentProvider}
                    />
                  </div>
                </TabPanel>
              } />
              <Route path="/sdapi" element={
                <TabPanel active={activeTab === "sdapi"} id="sdapi">
                  <SDApiPanel />
                </TabPanel>
              } />
              <Route path="/ollama" element={
                <TabPanel active={activeTab === "ollama"} id="ollama">
                  <OllamaApiPanel />
                </TabPanel>
              } />
              <Route path="/logs" element={
                <TabPanel active={activeTab === "logs"} id="logs">
                  <LogsPanel />
                </TabPanel>
              } />
            </Routes>
        </Tabs>
      </div>
    </div>
  );
}

export default App;

function AuthShell({ children }) {
  return (
    <div className="min-h-screen min-h-dvh w-full flex items-center justify-center p-24px box-border">
      <div className="auth-card">{children}</div>
    </div>
  );
}
