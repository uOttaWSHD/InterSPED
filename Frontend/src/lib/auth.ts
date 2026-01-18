import { betterAuth } from "better-auth";
import Database from "better-sqlite3";

const db = new Database("intersped.db");

export const auth = betterAuth({
    database: new Database("intersped.db"),
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
