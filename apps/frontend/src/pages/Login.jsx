import { BookOpen } from 'lucide-react';
import { login } from '../services/auth';
import './Login.css';

function Login({ onLogin }) {
  const handleLogin = () => {
    login();
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-icon">
          <BookOpen size={48} />
        </div>
        <h1>Notes App</h1>
        <p>Sign in to access your notes</p>
        
        <button onClick={handleLogin} className="login-btn">
          Sign in with Keycloak
        </button>
      </div>
    </div>
  );
}

export default Login;