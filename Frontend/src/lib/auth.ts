import { betterAuth } from "better-auth";
import { createClient } from "@libsql/client";

const client = createClient({
    url: process.env.TURSO_DATABASE_URL || "file:intersped.db",
    authToken: process.env.TURSO_AUTH_TOKEN,
});

export const auth = betterAuth({
    database: {
        db: client,
        type: "libsql",
    },
    trustedOrigins: ["http://127.0.0.1:3000", "http://localhost:3000"],
    socialProviders: {
        discord: {
            clientId: process.env.DISCORD_CLIENT_ID as string,
            clientSecret: process.env.DISCORD_CLIENT_SECRET as string,
        },
    },
    emailVerification: {
        autoSignInAfterVerification: true,
    },
});
