import { useState } from 'react';
import './Login.css';

export default function Login() {
    const [isRegistering, setIsRegistering] = useState(false);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setMessage('');

        const endpoint = isRegistering ? 'http://localhost:5001/api/register' : 'http://localhost:5001/api/login';

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            const data = await response.json();

            if (response.ok) {
                setMessage(isRegistering ? 'Registration successful! Please login.' : `Welcome back, ${data.user.email}!`);
                if (isRegistering) {
                    setIsRegistering(false);
                    setPassword('');
                }
            } else {
                setMessage(data.message || 'An error occurred');
            }
        } catch (error) {
            setMessage('Failed to connect to server');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="login-card">
            <div className="card-header">
                <h2>{isRegistering ? 'Create Account' : 'Welcome Back'}</h2>
                <p>{isRegistering ? 'Sign up to get started' : 'Enter your credentials to access your account'}</p>
            </div>

            <form onSubmit={handleSubmit}>
                <div className="form-group">
                    <label htmlFor="email">Email</label>
                    <input
                        type="email"
                        id="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="name@example.com"
                        required
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="password">Password</label>
                    <input
                        type="password"
                        id="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                    />
                </div>

                {message && <div className={`message ${message.includes('successful') || message.includes('Welcome') ? 'success' : 'error'}`}>{message}</div>}

                <button type="submit" className="submit-btn" disabled={isLoading}>
                    {isLoading ? 'Processing...' : (isRegistering ? 'Sign Up' : 'Sign In')}
                </button>
            </form>

            <div className="card-footer">
                <p>
                    {isRegistering ? 'Already have an account?' : "Don't have an account?"}
                    <button
                        type="button"
                        className="toggle-btn"
                        onClick={() => {
                            setIsRegistering(!isRegistering);
                            setMessage('');
                        }}
                    >
                        {isRegistering ? 'Sign In' : 'Sign Up'}
                    </button>
                </p>
            </div>
        </div>
    );
}
