import { useAuth0 } from "@auth0/auth0-react";
import { useEffect, useState } from "react";
import LoginButton from "./LoginButton";
import SignUpButton from "./components/auth/SignUpButton";
import LogoutButton from "./components/auth/LogoutButton";
import ChatPanel from "./components/chat/ChatPanel";
import DemoChat from "./components/chat/DemoChat";
import ConversationList from "./components/conversations/ConversationList";
import ConnectionStatus from "./components/controls/ConnectionStatus";
import TranscriptUpload from "./components/transcripts/TranscriptUpload";
import ModelSettings from "./components/settings/ModelSettings";
import Tabs from "./components/Tabs";
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

  // Store auth token globally for API calls
  useEffect(() => {
    if (isAuthenticated) {
      getIdTokenClaims()
        .then((claims) => {
          window.authToken = claims.__raw;
        })
        .catch((err) => {
          console.error("Failed to get access token:", err);
        });
    } else {
      window.authToken = null;
    }
  }, [isAuthenticated, getIdTokenClaims]);

  // Check if user has admin role via backend API
  useEffect(() => {
    const checkAccess = async () => {
      if (!isAuthenticated || !user) {
        setHasAccess(false);
        setCheckingAccess(false);
        return;
      }

      try {
        // Get access token for API call
        const claims = await getIdTokenClaims();
        const idToken = claims.__raw; // Get raw ID token string
        if (!idToken) {
          setHasAccess(false);
          setCheckingAccess(false);
          return;
        }

        // Call backend API to check admin role
        const response = await fetch("/api/v1/auth/check-admin", {
          headers: {
            Authorization: `Bearer ${idToken}`,
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          console.error(
            "Failed to check admin role:",
            response.status,
            errorData
          );
          setHasAccess(false);
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
        setHasAccess(false);
      } finally {
        setCheckingAccess(false);
      }
    };

    checkAccess();
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

  const tabs = [
    { id: "chat", label: "Chat", icon: "" },
    { id: "sessions", label: "Sessions", icon: "" },
    { id: "transcripts", label: "Transcripts", icon: "" },
    { id: "settings", label: "Settings", icon: "" },
  ];

  const handleSessionSelect = (sessionId) => {
    setSelectedSessionId(sessionId);
    setActiveTab("chat");
  };

  const handleModelChange = (model) => {
    setCurrentModel(model);
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
            <ModelSettings
              currentModel={currentModel}
              onModelChange={handleModelChange}
            />
          )}
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
