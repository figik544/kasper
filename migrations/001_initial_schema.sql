-- Initial schema for Galactic Empire Federation database

-- Table for federation applications
CREATE TABLE federation_applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  server_name TEXT NOT NULL,
  owner_nickname TEXT NOT NULL,
  server_description TEXT,
  server_type TEXT,
  server_population INTEGER,
  discord_invite TEXT,
  discord_user_id TEXT NOT NULL,
  discord_server_id TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  approved_at DATETIME NULL
);

-- Table for server settings
CREATE TABLE server_settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  guild_id INTEGER UNIQUE,
  bot_status TEXT DEFAULT 'online',
  prefix TEXT DEFAULT '!',
  welcome_message TEXT,
  auto_moderation BOOLEAN DEFAULT 1,
  spam_threshold INTEGER DEFAULT 5,
  max_warnings INTEGER DEFAULT 5,
  daily_credits_min INTEGER DEFAULT 50,
  daily_credits_max INTEGER DEFAULT 150,
  salary_interval INTEGER DEFAULT 24,
  advertising_enabled BOOLEAN DEFAULT 1,
  ad_message TEXT,
  ad_frequency INTEGER DEFAULT 6,
  elections_enabled BOOLEAN DEFAULT 0,
  legislation_enabled BOOLEAN DEFAULT 0,
  election_cycle INTEGER DEFAULT 30,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table for political events
CREATE TABLE political_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  start_date DATETIME,
  end_date DATETIME,
  status TEXT DEFAULT 'scheduled',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table for users (from the Discord bot database)
CREATE TABLE users (
  user_id INTEGER PRIMARY KEY,
  guild_id INTEGER,
  level INTEGER DEFAULT 1,
  xp INTEGER DEFAULT 0,
  credits INTEGER DEFAULT 0,
  rank TEXT DEFAULT 'Recruit',
  join_date DATETIME,
  last_daily_claim DATETIME,
  warnings INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX idx_federation_applications_status ON federation_applications(status);
CREATE INDEX idx_federation_applications_created ON federation_applications(created_at);
CREATE INDEX idx_users_guild_level ON users(guild_id, level DESC);