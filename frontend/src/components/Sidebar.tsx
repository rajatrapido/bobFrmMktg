"use client";
import Link from 'next/link';
import { useAuth } from './AuthProvider';

const Sidebar = () => {
    const { user, signIn, logout } = useAuth();

    return (
        <div className="sidebar" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div className="logo">BobFrmMktg</div>
            <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <Link href="/" className="nav-item active">
                    Time Diff
                </Link>
                <Link href="/weekly-bids" className="nav-item">
                    Weekly Bids
                </Link>
                <Link href="/creative" className="nav-item">
                    Creative
                </Link>
                <Link href="/gen-images" className="nav-item">
                    Gen Images
                </Link>
                <Link href="/gen-copies" className="nav-item">
                    Gen Copies
                </Link>
                {user && (
                    <Link href="/admin/settings" className="nav-item" style={{ marginTop: 'auto', borderTop: '1px solid var(--border)' }}>
                        Config
                    </Link>
                )}
            </nav>

            <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border)', fontSize: '0.875rem' }}>
                {user ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            <strong>{user.email}</strong>
                        </div>
                        <button onClick={logout} style={{ background: 'transparent', border: '1px solid var(--border)', padding: '0.5rem', borderRadius: '4px', cursor: 'pointer', color: 'var(--text)' }}>
                            Sign Out
                        </button>
                    </div>
                ) : (
                    <button onClick={signIn} style={{ width: '100%', background: 'var(--primary)', color: 'white', border: 'none', padding: '0.5rem', borderRadius: '4px', cursor: 'pointer' }}>
                        Sign in with Google
                    </button>
                )}
            </div>
        </div>
    );
};

export default Sidebar;
