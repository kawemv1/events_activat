import initSqlJs, { Database } from 'sql.js';

let dbInstance: Database | null = null;

export interface User {
  username: string;
  name: string;
  surname: string;
}

async function initDatabase(): Promise<Database> {
  if (dbInstance) {
    return dbInstance;
  }

  try {
    const SQL = await initSqlJs({
      locateFile: (file: string) => {
        if (file.endsWith('.wasm')) {
          return `/${file}`;
        }
        return `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`;
      }
    });

    // Try to fetch existing database, or create new one
    try {
      const response = await fetch('/users.db');
      if (response.ok) {
        const buffer = await response.arrayBuffer();
        const uint8Array = new Uint8Array(buffer);
        dbInstance = new SQL.Database(uint8Array);
      } else {
        throw new Error('Database not found');
      }
    } catch (error) {
      // Create new database if fetch fails
      dbInstance = new SQL.Database();
      dbInstance.run(`
        CREATE TABLE IF NOT EXISTS users (
          username TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          surname TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `);
      // Insert sample account (password: Test123, base64 encoded)
      dbInstance.run(`
        INSERT OR IGNORE INTO users (username, name, surname, password_hash) 
        VALUES ('kawemv1', 'Ansar', 'Kairzhan', 'VGVzdDEyMw==')
      `);
    }

    return dbInstance;
  } catch (error) {
    console.error('Error initializing auth database:', error);
    throw error;
  }
}

// Simple password hashing (in production, use bcrypt)
function hashPassword(password: string): string {
  // Simple hash for demo - in production use bcrypt
  return btoa(password);
}

function verifyPassword(password: string, hash: string): boolean {
  return btoa(password) === hash;
}

export async function login(username: string, password: string): Promise<User | null> {
  try {
    const db = await initDatabase();
    // sql.js doesn't support parameterized queries the same way, use string interpolation with escaping
    const escapedUsername = username.replace(/'/g, "''");
    const result = db.exec(`SELECT username, name, surname, password_hash FROM users WHERE username = '${escapedUsername}'`);
    
    console.log('Login query result:', result);
    
    if (result.length === 0 || !result[0].values.length) {
      console.log('No user found with username:', username);
      return null;
    }

    const columns = result[0]['lc'] || result[0].columns;
    const values = result[0].values;
    const row = values[0];
    
    // Find column indices
    const usernameIdx = columns.indexOf('username');
    const nameIdx = columns.indexOf('name');
    const surnameIdx = columns.indexOf('surname');
    const passwordHashIdx = columns.indexOf('password_hash');
    
    const passwordHash = row[passwordHashIdx] as string;
    console.log('Stored hash:', passwordHash, 'Input password:', password, 'Computed hash:', btoa(password));
    
    if (verifyPassword(password, passwordHash)) {
      return {
        username: row[usernameIdx] as string,
        name: row[nameIdx] as string,
        surname: row[surnameIdx] as string,
      };
    }
    
    console.log('Password verification failed');
    return null;
  } catch (error) {
    console.error('Login error:', error);
    return null;
  }
}

export async function signup(username: string, name: string, surname: string, password: string): Promise<boolean> {
  try {
    const db = await initDatabase();
    const passwordHash = hashPassword(password);
    
    // Escape single quotes for SQL
    const escapedUsername = username.replace(/'/g, "''");
    const escapedName = name.replace(/'/g, "''");
    const escapedSurname = surname.replace(/'/g, "''");
    const escapedHash = passwordHash.replace(/'/g, "''");
    
    db.run(`INSERT INTO users (username, name, surname, password_hash) VALUES ('${escapedUsername}', '${escapedName}', '${escapedSurname}', '${escapedHash}')`);
    
    return true;
  } catch (error) {
    console.error('Signup error:', error);
    return false;
  }
}

export async function userExists(username: string): Promise<boolean> {
  try {
    const db = await initDatabase();
    const escapedUsername = username.replace(/'/g, "''");
    const result = db.exec(`SELECT username FROM users WHERE username = '${escapedUsername}'`);
    return result.length > 0 && result[0].values.length > 0;
  } catch (error) {
    console.error('User exists check error:', error);
    return false;
  }
}
