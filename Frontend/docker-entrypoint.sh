#!/bin/sh
set -e

# Ensure the directory for the database exists
if [ -n "$DATABASE_PATH" ]; then
    DB_DIR=$(dirname "$DATABASE_PATH")
    echo "Ensuring directory $DB_DIR exists..."
    mkdir -p "$DB_DIR" || echo "Warning: Could not create $DB_DIR. It might already exist or be read-only."
fi

# Run migrations if DATABASE_PATH is set and we have the CLI
if [ -f "node_modules/.bin/better-auth" ] || [ -f "node_modules/better-auth/dist/cli.js" ]; then
    echo "Running database migrations..."
    npx better-auth migrate --yes
else
    echo "Better Auth CLI not found, skipping migrations. Ensure they are run manually if needed."
fi

# Start the application
exec node server.js
