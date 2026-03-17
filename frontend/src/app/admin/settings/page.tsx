"use client";

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';

function AdminSettingsContent() {
    const { user, loading, getToken } = useAuth();
    const [connecting, setConnecting] = useState(false);
    const [message, setMessage] = useState('');
    const searchParams = useSearchParams();
    const router = useRouter();

    const handleOAuthCallback = async (code: string) => {
        setConnecting(true);
        setMessage('Completing Google Ads authorization...');
        try {
            const token = await getToken();
            const res = await fetch('http://localhost:8000/auth/adwords/callback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ code })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                setMessage('Successfully connected to Google Ads!');
                router.replace('/admin/settings');
            } else {
                setMessage(`Failed to connect: ${data.detail || 'Unknown error'}`);
            }
        } catch (err) {
            setMessage('Network error during callback.');
        } finally {
            setConnecting(false);
        }
    };

    useEffect(() => {
        const code = searchParams.get('code');
        if (code && user) {
            handleOAuthCallback(code);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [searchParams, user]);

    const handleConnectAds = async () => {
        setConnecting(true);
        try {
            const token = await getToken();
            const res = await fetch('http://localhost:8000/auth/adwords/login', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            if (data.auth_url) {
                window.location.href = data.auth_url;
            } else {
                setMessage('Failed to get authorization URL.');
            }
        } catch (err) {
            setMessage('Network error attempting to connect.');
        } finally {
            setConnecting(false);
        }
    };

    if (loading) return <div>Loading...</div>;

    if (!user) {
        return <div style={{ padding: '2rem' }}>You must be logged in to view Admin Settings.</div>;
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
            <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '2rem' }}>Admin Configuration</h1>

            <section style={{
                background: 'var(--bg-card, #ffffff)',
                padding: '2rem',
                borderRadius: '0.5rem',
                boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
            }}>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 'semibold', marginBottom: '1rem' }}>Google Ads Integration</h2>
                <p style={{ color: 'var(--text-dim, #666)', marginBottom: '2rem' }}>
                    Connect your system to Google Ads to programmatically fetch marketing performance reports. You must be an administrator inside your Google Ads account to authorize this integration.
                </p>

                {message && (
                    <div style={{ padding: '1rem', background: '#e0f2fe', color: '#0369a1', borderRadius: '0.25rem', marginBottom: '1rem' }}>
                        {message}
                    </div>
                )}

                <button
                    onClick={handleConnectAds}
                    disabled={connecting}
                    style={{
                        background: 'var(--primary, #2563eb)',
                        color: 'white',
                        padding: '0.75rem 1.5rem',
                        borderRadius: '0.25rem',
                        border: 'none',
                        cursor: connecting ? 'not-allowed' : 'pointer',
                        fontWeight: '500',
                        opacity: connecting ? 0.7 : 1
                    }}
                >
                    {connecting ? 'Connecting...' : 'Connect to Google Ads'}
                </button>
            </section>
        </div>
    );
}

export default function AdminSettings() {
    return (
        <Suspense fallback={<div>Loading settings...</div>}>
            <AdminSettingsContent />
        </Suspense>
    );
}
