import React from "react";
import ReactDOM from "react-dom/client";
import { Auth0Provider } from "@auth0/auth0-react";
import App from "./App.jsx";
import "./styles/index.css";

const domain = import.meta.env.VITE_AUTH0_DOMAIN;
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID;
const audience = import.meta.env.VITE_AUTH0_AUDIENCE;

// Validate Auth0 configuration
if (!domain || !clientId) {
  console.error("Auth0 configuration missing. Please check your .env file.");
  console.error("Required environment variables:");
  console.error("- VITE_AUTH0_DOMAIN");
  console.error("- VITE_AUTH0_CLIENT_ID");
  throw new Error("Auth0 domain and client ID must be set in .env file");
}

// Validate domain format
if (
  !domain.includes(".auth0.com") &&
  !domain.includes(".us.auth0.com") &&
  !domain.includes(".eu.auth0.com") &&
  !domain.includes(".au.auth0.com")
) {
  console.warn(
    "Auth0 domain format might be incorrect. Expected format: your-domain.auth0.com"
  );
}

// Construct redirect_uri - ensure it's a valid URI
const getRedirectUri = () => {
  // Allow override via environment variable
  const envRedirectUri = import.meta.env.VITE_AUTH0_REDIRECT_URI;
  if (envRedirectUri) {
    return envRedirectUri;
  }

  // Construct from current location
  const protocol = window.location.protocol;
  const host = window.location.host;

  if (!protocol || !host) {
    console.error("Unable to determine redirect_uri from window.location");
    throw new Error(
      "Unable to determine redirect_uri. Please set VITE_AUTH0_REDIRECT_URI in .env file"
    );
  }

  // Construct full URI (protocol + host, no trailing slash)
  const redirectUri = `${protocol}//${host}`;

  // Validate it's a proper URI
  try {
    new URL(redirectUri);
    return redirectUri;
  } catch (e) {
    console.error("Invalid redirect_uri constructed:", redirectUri);
    throw new Error(
      `Invalid redirect_uri: ${redirectUri}. Please set VITE_AUTH0_REDIRECT_URI in .env file`
    );
  }
};

const redirectUri = getRedirectUri();
console.log("Auth0 redirect_uri:", redirectUri);

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

// Build authorizationParams object
const authorizationParams = {
  redirect_uri: redirectUri,
};

// Don't add audience - this will make tokens be ID tokens instead

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <Auth0Provider
      domain={domain}
      clientId={clientId}
      authorizationParams={authorizationParams}
      useRefreshTokens={true}
      cacheLocation="localstorage"
    >
      <App />
    </Auth0Provider>
  </React.StrictMode>
);
