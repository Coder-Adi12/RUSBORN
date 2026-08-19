import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.login({ username, password });
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: '#0a0a0b', color: '#fff' }}>
      <div style={{ width: '400px', padding: '2rem', background: '#121214', borderRadius: '12px', border: '1px solid #27272a' }}>
        <h2 style={{ marginBottom: '1.5rem', textAlign: 'center' }}>RUSBORN Operations</h2>
        {error && <div style={{ color: '#ef4444', marginBottom: '1rem', textAlign: 'center' }}>{error}</div>}
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Username</label>
            <input 
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', background: '#18181b', border: '1px solid #3f3f46', color: '#fff' }}
              required 
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Password</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', background: '#18181b', border: '1px solid #3f3f46', color: '#fff' }}
              required 
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            style={{ marginTop: '1rem', padding: '0.75rem', borderRadius: '6px', background: '#3b82f6', color: '#fff', border: 'none', cursor: loading ? 'not-allowed' : 'pointer' }}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
