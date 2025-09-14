CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    disaster_type TEXT,
    description TEXT,
    location TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);