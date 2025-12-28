import { useAuth0 } from "@auth0/auth0-react";
import { useEffect, useState } from "react";
import LoginButton from "./components/auth/LoginButton";
import SignUpButton from "./components/auth/SignUpButton";
import LogoutButton from "./components/auth/LogoutButton";
import ChatPanel from "./components/chat/ChatPanel";
import DemoChat from "./components/chat/DemoChat";
import ConversationList from "./components/conversations/ConversationList";
import ConnectionStatus from "./components/controls/ConnectionStatus";
import TelegramStatus from "./components/controls/TelegramStatus";
import ProviderSelector from "./components/controls/ProviderSelector";
import TranscriptUpload from "./components/transcripts/TranscriptUpload";
import ModelSettings from "./components/settings/ModelSettings";
import LogsPanel from "./components/logs/LogsPanel";
import SDApiPanel from "./components/api/SDApiPanel";
import OllamaApiPanel from "./components/api/OllamaApiPanel";
import IdentityPanel from "./components/identity/IdentityPanel";
import UserMemoryPanel from "./components/memory/UserMemoryPanel";
import AgentPanel from "./components/agent/AgentPanel";
import Tabs from "./components/Tabs";
import { apiGet } from "./services/api";
import "./styles/App.css";

function App() {
  const {
    isAuthenticated,
    isLoading,
    error,
    getAccessTokenSilently,
    user,
    getIdTokenClaims,
  } = useAuth0();
  const [hasAccess, setHasAccess] = useState(false);
  const [checkingAccess, setCheckingAccess] = useState(true);

  // Store auth token globally for API calls and set up refresh mechanism
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
          
          window.authToken = claims.__raw;
          
          // Don't trigger access check here - it causes circular loops
          // Access check will use the refreshed token automatically via apiGet
          
          return claims.__raw;
        } catch (err) {
          console.error("Failed to refresh token:", err);
          window.authToken = null;
          throw err;
        }
      };

      // Initial token fetch
      refreshToken().catch((err) => {
        console.error("Initial token fetch failed:", err);
      });

      // Set up global token refresh function for API service
      window.refreshAuthToken = refreshToken;

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
        window.refreshAuthToken = null;
        window.triggerAccessCheck = null;
      };
    } else {
      window.authToken = null;
      window.refreshAuthToken = null;
      window.triggerAccessCheck = null;
    }
  }, [isAuthenticated, getIdTokenClaims, getAccessTokenSilently]);

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
        // Ensure we have a token - apiGet will handle refresh automatically if needed
        if (!window.authToken) {
          try {
            const claims = await getIdTokenClaims();
            if (claims && claims.__raw) {
              window.authToken = claims.__raw;
            }
          } catch (e) {
            console.warn("Failed to get initial token, apiGet will handle refresh:", e);
          }
        }

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

        setHasAccess(data.has_admin_role === true);
      } catch (err) {
        console.error("Failed to check user roles:", err);
        // Don't retry here - apiGet already handles retry with token refresh
        // If it still fails after retry, the token is likely invalid
        setHasAccess(false);
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
        <div className="auth-status">Loading...</div>
      </AuthShell>
    );
  }

  if (error) {
    return (
      <AuthShell>
        <div className="auth-status-title">Authentication Error</div>
        <div className="auth-status-subtitle">{error.message}</div>
        <div className="auth-actions">
          <button
            className="auth-primary-button"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </AuthShell>
    );
  }

  if (!isAuthenticated) {
    return <DemoInterface />;
  }

  // Check access - only allow users with admin role
  if (!hasAccess) {
    return (
      <AuthShell>
        <div className="auth-hero">
          <div className="auth-title">Access denied</div>
          <div className="auth-subtitle">
            Your account is not authorized for this app.
          </div>
        </div>
        <div className="auth-divider" />
        <div className="auth-note">
          Signed in as{" "}
          <span className="auth-email">{user?.email || "Unknown"}</span>
        </div>
        <div
          className="auth-note"
          style={{ fontSize: "0.85em", marginTop: "10px", color: "#999" }}
        >
          Please check the browser console (F12) for detailed error information.
          <br />
          You need the "admin" role assigned in Auth0 to access this
          application.
        </div>
        <div className="auth-actions">
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
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="title-section">
            <h1>ARES</h1>
            <div className="subtitle">AI Orchestration and Control System</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <LoginButton />
            <SignUpButton />
          </div>
        </div>
      </header>

      <div className="main-content">
        <DemoChat />
      </div>
    </div>
  );
}

function MainInterface() {
  const [activeTab, setActiveTab] = useState("chat");
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [currentModel, setCurrentModel] = useState("");
  const [currentProvider, setCurrentProvider] = useState("local");

  const tabs = [
    { id: "chat", label: "Chat", icon: "" },
    { id: "agent", label: "Agent", icon: "" },
    { id: "identity", label: "Identity", icon: "" },
    { id: "memory", label: "Memory", icon: "" },
    { id: "sessions", label: "Sessions", icon: "" },
    { id: "transcripts", label: "Transcripts", icon: "" },
    { id: "sdapi", label: "SD API", icon: "" },
    { id: "ollama", label: "Ollama", icon: "" },
    { id: "settings", label: "Settings", icon: "" },
    { id: "logs", label: "Logs", icon: "" },
  ];

  const handleSessionSelect = (sessionId) => {
    setSelectedSessionId(sessionId);
    setActiveTab("chat");
  };

  const handleModelChange = (model) => {
    setCurrentModel(model);
  };

  const handleProviderChange = (provider) => {
    setCurrentProvider(provider);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <div className="title-section">
            <h1>ARES</h1>
            <div className="subtitle">AI Orchestration and Control System</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
            <ConnectionStatus />
            <TelegramStatus />
            <LogoutButton />
          </div>
        </div>
      </header>

      <div className="main-content">
        <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab}>
          {activeTab === "chat" && (
            <ChatPanel
              sessionId={selectedSessionId}
              onSessionChange={setSelectedSessionId}
            />
          )}
          {activeTab === "agent" && <AgentPanel />}
          {activeTab === "identity" && <IdentityPanel />}
          {activeTab === "memory" && <UserMemoryPanel />}
          {activeTab === "sessions" && (
            <div className="panel panel-fill">
              <ConversationList
                onSelectSession={handleSessionSelect}
                selectedSessionId={selectedSessionId}
              />
            </div>
          )}
          {activeTab === "transcripts" && (
            <TranscriptUpload
              onSummaryGenerated={(summary, filename) => {
                console.log("Summary generated:", summary, filename);
              }}
            />
          )}
          {activeTab === "settings" && (
            <div className="panel panel-fill">
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
          )}
          {activeTab === "sdapi" && <SDApiPanel />}
          {activeTab === "ollama" && <OllamaApiPanel />}
          {activeTab === "logs" && <LogsPanel />}
        </Tabs>
      </div>
    </div>
  );
}

export default App;

function AuthShell({ children }) {
  return (
    <div className="auth-page">
      <div className="auth-card">{children}</div>
    </div>
  );
}
