import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { AuthProvider } from '../contexts/AuthContext';
import { jsonResponse, mockFetch } from '../test/fetchMock';
import LoginPage from './LoginPage';

const USER = {
  _id: 'u1', email: 'viewer@procureai.test', full_name: 'Viewer', is_active: true,
  is_superuser: false, role: 'viewer', created_at: '2026-01-01T00:00:00Z',
};

function renderLogin(language: 'en' | 'gr' = 'en') {
  return render(
    <AuthProvider>
      <LoginPage language={language} onToggleLanguage={() => {}} />
    </AuthProvider>,
  );
}

const ready = () => jsonResponse({ status: 'ready', checks: { mongo: 'ok' } });

describe('LoginPage', () => {
  it('asks for both fields without calling the API', async () => {
    const spy = mockFetch({ 'GET /health/ready': ready });
    renderLogin();

    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(screen.getByTestId('login-error')).toHaveTextContent('Enter your email and password.');
    expect(spy.mock.calls.some(([u]) => String(u).endsWith('/auth/login'))).toBe(false);
    expect(screen.getByLabelText('Email')).toHaveFocus();
  });

  it('shows a generic message on 401 and clears the password', async () => {
    mockFetch({
      'GET /health/ready': ready,
      'POST /auth/login': () => jsonResponse({ detail: 'User not found' }, 401),
    });
    renderLogin();

    await userEvent.type(screen.getByLabelText('Email'), 'a@b.gr');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByTestId('login-error')).toHaveTextContent('Wrong email or password.');
    expect(screen.queryByText('User not found')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toHaveValue('');
  });

  it('shows an availability message on server errors', async () => {
    mockFetch({
      'GET /health/ready': ready,
      'POST /auth/login': () => jsonResponse({ detail: 'boom' }, 500),
    });
    renderLogin();

    await userEvent.type(screen.getByLabelText('Email'), 'a@b.gr');
    await userEvent.type(screen.getByLabelText('Password'), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByTestId('login-error')).toHaveTextContent(/not available right now/);
  });

  it('sends trimmed credentials on submit', async () => {
    const spy = mockFetch({
      'GET /health/ready': ready,
      'POST /auth/login': () => jsonResponse({ access_token: 't', user: USER }),
    });
    renderLogin();

    await userEvent.type(screen.getByLabelText('Email'), '  viewer@procureai.test ');
    await userEvent.type(screen.getByLabelText('Password'), 'secret');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      const call = spy.mock.calls.find(([u]) => String(u).endsWith('/auth/login'));
      expect(JSON.parse(String((call?.[1] as RequestInit).body))).toEqual({ email: 'viewer@procureai.test', password: 'secret' });
    });
  });

  it('toggles password visibility', async () => {
    mockFetch({ 'GET /health/ready': ready });
    renderLogin();

    const input = screen.getByLabelText('Password');
    expect(input).toHaveAttribute('type', 'password');
    await userEvent.click(screen.getByRole('button', { name: 'Show password' }));
    expect(input).toHaveAttribute('type', 'text');
    expect(screen.getByRole('button', { name: 'Hide password' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('reports backend status from /health/ready', async () => {
    mockFetch({ 'GET /health/ready': ready });
    renderLogin();
    await waitFor(() => expect(screen.getByTestId('backend-status')).toHaveAttribute('data-status', 'ready'));
  });

  it('reports an unreachable backend', async () => {
    mockFetch({});
    renderLogin();
    await waitFor(() => expect(screen.getByTestId('backend-status')).toHaveAttribute('data-status', 'offline'));
    expect(screen.getByTestId('backend-status')).toHaveTextContent('Backend unreachable');
  });

  it('renders Greek text', () => {
    mockFetch({ 'GET /health/ready': ready });
    renderLogin('gr');
    expect(screen.getByRole('heading', { name: 'Είσοδος' })).toBeInTheDocument();
    expect(screen.getByLabelText('Κωδικός')).toBeInTheDocument();
  });
});
