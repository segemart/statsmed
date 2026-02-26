'use client';

import { useState, useEffect, FormEvent } from 'react';
import Image from 'next/image';
import { loginUser, registerUser } from '../lib/api';
import styles from './LandingPage.module.css';

import logoImg from '../../Icon/NewIcon.png';

interface LandingPageProps {
  children?: React.ReactNode;
  section?: 'data-analysis' | 'quality-control';
  onSectionChange?: (section: 'data-analysis' | 'quality-control') => void;
}

export default function LandingPage({ children, section = 'data-analysis', onSectionChange }: LandingPageProps) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [registerSuccess, setRegisterSuccess] = useState(false);
  const [registerMessage, setRegisterMessage] = useState('');
  const [registerError, setRegisterError] = useState('');
  const [registerLoading, setRegisterLoading] = useState(false);
  const [currentUser, setCurrentUser] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regPasswordConfirm, setRegPasswordConfirm] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('statsmed_token');
    const saved = localStorage.getItem('statsmed_user');
    if (token && saved) {
      setIsLoggedIn(true);
      setCurrentUser(saved);
    }
  }, []);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLoginError('');
    if (!username.trim() || !password.trim()) {
      setLoginError('Please enter username and password.');
      return;
    }
    setLoginLoading(true);
    try {
      const res = await loginUser(username, password);
      if (res.success && res.username && res.token) {
        localStorage.setItem('statsmed_token', res.token);
        localStorage.setItem('statsmed_user', res.username);
        setIsLoggedIn(true);
        setCurrentUser(res.username);
        setUsername('');
        setPassword('');
      }
    } catch (err: unknown) {
      setLoginError(err instanceof Error ? err.message : 'Login failed.');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('statsmed_token');
    localStorage.removeItem('statsmed_user');
    setIsLoggedIn(false);
    setCurrentUser('');
  };

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault();
    setRegisterError('');
    if (!regUsername.trim() || !regEmail.trim() || !regPassword.trim()) {
      setRegisterError('Please fill in all fields.');
      return;
    }
    if (regPassword !== regPasswordConfirm) {
      setRegisterError('Passwords do not match.');
      return;
    }
    if (regPassword.length < 6) {
      setRegisterError('Password must be at least 6 characters.');
      return;
    }
    setRegisterLoading(true);
    try {
      const res = await registerUser(regUsername, regEmail, regPassword);
      setRegisterSuccess(true);
      setRegisterMessage(res.message);
      setTimeout(() => {
        setShowRegister(false);
        setRegisterSuccess(false);
        setRegisterMessage('');
        setRegUsername('');
        setRegEmail('');
        setRegPassword('');
        setRegPasswordConfirm('');
      }, 3000);
    } catch (err: unknown) {
      setRegisterError(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setRegisterLoading(false);
    }
  };

  return (
    <>
      <header className={styles.topBar}>
        <div className={styles.logo}>
          <Image src={logoImg} alt="Statsmed" className={styles.logoIcon} width={36} height={36} priority />
          Statsmed
          <span className={styles.logoSubtitle}>Statistics for Medical Data</span>
        </div>

        {isLoggedIn ? (
          <>
            <nav className={styles.navOptions}>
              <button
                type="button"
                className={section === 'data-analysis' ? styles.navOptionActive : styles.navOption}
                onClick={() => onSectionChange?.('data-analysis')}
              >
                Data analysis
              </button>
              <button
                type="button"
                className={section === 'quality-control' ? styles.navOptionActive : styles.navOption}
                onClick={() => onSectionChange?.('quality-control')}
              >
                Quality control
              </button>
            </nav>
            <div className={styles.userInfo}>
              <span className={styles.userName}>
                Welcome, <strong>{currentUser}</strong>
              </span>
              <button className={styles.logoutButton} onClick={handleLogout}>
                Log Out
              </button>
            </div>
          </>
        ) : (
          <form className={styles.loginForm} onSubmit={handleLogin}>
            <input
              type="text"
              className={styles.inputField}
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
            <input
              type="password"
              className={styles.inputField}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
            <button
              type="submit"
              className={styles.loginButton}
              disabled={loginLoading}
            >
              {loginLoading ? '...' : 'Sign In'}
            </button>
            <span className={styles.divider} />
            <a
              className={styles.registerLink}
              onClick={() => setShowRegister(true)}
              role="button"
            >
              Register
            </a>
          </form>
        )}

        {loginError && (
          <div className={styles.errorMessage}>{loginError}</div>
        )}
      </header>

      {isLoggedIn ? (
        <div className={styles.dashboardWrapper}>{children}</div>
      ) : (
        <main className={styles.landingContent}>
          <div className={styles.heroSection}>
            <h1 className={styles.heroTitle}>
              Statistical analysis and quality control for medical data
            </h1>
          </div>
          <footer className={styles.footer}>
            <p>© {new Date().getFullYear()} Statsmed</p>
          </footer>
        </main>
      )}

      {showRegister && (
        <div
          className={styles.modalOverlay}
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowRegister(false);
          }}
        >
          <div className={styles.modalCard}>
            {registerSuccess ? (
              <div className={styles.successMessage}>
                <span className={styles.successIcon}>✓</span>
                <p className={styles.successText}>
                  {registerMessage || 'Registration successful!'}
                </p>
              </div>
            ) : (
              <>
                <h2 className={styles.modalTitle}>Create Account</h2>
                <p className={styles.modalSubtitle}>
                  Sign up for Statsmed. All uploaded data is saved to your account.
                </p>
                {registerError && (
                  <div className={styles.errorMessage} style={{
                    position: 'relative', top: 0, right: 0, marginBottom: '16px', display: 'block',
                  }}>
                    {registerError}
                  </div>
                )}
                <form onSubmit={handleRegister}>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Username</label>
                    <input
                      type="text"
                      className={styles.formInput}
                      placeholder="Min. 3 characters"
                      value={regUsername}
                      onChange={(e) => setRegUsername(e.target.value)}
                      required
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Email</label>
                    <input
                      type="email"
                      className={styles.formInput}
                      placeholder="your@email.com"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Password</label>
                    <input
                      type="password"
                      className={styles.formInput}
                      placeholder="At least 6 characters"
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      required
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Confirm Password</label>
                    <input
                      type="password"
                      className={styles.formInput}
                      placeholder="Repeat password"
                      value={regPasswordConfirm}
                      onChange={(e) => setRegPasswordConfirm(e.target.value)}
                      required
                    />
                  </div>
                  <div className={styles.modalActions}>
                    <button
                      type="submit"
                      className={styles.registerButton}
                      disabled={registerLoading}
                    >
                      {registerLoading ? 'Creating...' : 'Register'}
                    </button>
                    <button
                      type="button"
                      className={styles.cancelButton}
                      onClick={() => { setShowRegister(false); setRegisterError(''); }}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
