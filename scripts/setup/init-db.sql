-- ============================================================================
-- Vayuntra — PostgreSQL Initialization Script
-- Auto-executed by Docker when postgres container first starts
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create TimescaleDB extension (only for timescaledb container)
-- CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Set timezone
SET timezone = 'UTC';

-- Grant privileges (user already created by POSTGRES_USER env var)
GRANT ALL PRIVILEGES ON DATABASE vayuntra TO vayuntra_app;
GRANT ALL ON SCHEMA public TO vayuntra_app;

-- Note: Tables are created by SQLAlchemy on startup (init_db())
-- This script only handles extensions and permissions.
