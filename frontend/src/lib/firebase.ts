// Bypassed for testing
export const signInWithGoogle = async () => { };
export const signOut = async () => { };

// Return a dummy auth object that looks like the Firebase auth object
export const auth: any = {
    currentUser: {
        uid: "mock",
        email: "mock",
        getIdToken: async () => "mock",
    }
};

