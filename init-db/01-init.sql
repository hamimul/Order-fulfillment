-- Create database if it doesn't exist
CREATE DATABASE order_fulfillment;

-- Create a user for the application
CREATE USER app_user WITH PASSWORD 'app_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE order_fulfillment TO app_user;

-- Connect to the database
\c order_fulfillment;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO app_user;