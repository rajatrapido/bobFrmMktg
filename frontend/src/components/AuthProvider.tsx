"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
// Bypassing real Firebase auth for testing purposes
// import { User, onAuthStateChanged } from "firebase/auth";
// import { auth, signInWithGoogle, signOut } from "../lib/firebase";

// Mock User type since we aren't importing from firebase/auth
interface User {
    uid: string;
    email: string | null;
    displayName: string | null;
    getIdToken: () => Promise<string>;
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    signIn: () => Promise<void>;
    logout: () => Promise<void>;
    getToken: () => Promise<string | null>;
}

const mockUser: User = {
    uid: "mock-user-123",
    email: "testuser@example.com",
    displayName: "Test User",
    getIdToken: async () => "mock-token"
};

const AuthContext = createContext<AuthContextType>({
    user: mockUser,
    loading: false,
    signIn: async () => { },
    logout: async () => { },
    getToken: async () => "mock-token",
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
    // Always return the mock user to bypass auth
    const [user, setUser] = useState<User | null>(mockUser);
    const [loading, setLoading] = useState(false);

    const signIn = async () => {
        setUser(mockUser);
    };

    const logout = async () => {
        setUser(null);
    };

    const getToken = async () => {
        return "mock-token";
    };

    return (
        <AuthContext.Provider value={{ user, loading, signIn, logout, getToken }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
