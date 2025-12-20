import { useAuth0 } from "@auth0/auth0-react";
import './components/auth/Auth.css';

const LoginButton = () => {
  const { loginWithRedirect, isAuthenticated } = useAuth0();
  
  if (isAuthenticated) {
    return null;
  }
  
  return (
    <button 
      onClick={() => loginWithRedirect()} 
      className="auth-button login-button"
    >
      Log In
    </button>
  );
};

export default LoginButton;
