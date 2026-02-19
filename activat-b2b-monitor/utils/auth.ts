import { supabaseGet, supabasePost } from './supabase';

export interface User {
  id: number;
  username: string;
  name: string;
  surname: string;
}

interface AuthUserRow {
  username: string;
  name: string;
  surname: string;
  password_hash: string;
}

interface UserRow {
  id: number;
  telegram_id: number | null;
  username: string | null;
  first_name: string | null;
}

function hashPassword(password: string): string {
  return btoa(password);
}

function verifyPassword(password: string, hash: string): boolean {
  return btoa(password) === hash;
}

// Get or create user in users table for web app user
async function getOrCreateWebUser(username: string, name: string, surname: string): Promise<number> {
  // Check if user exists in users table (web users have telegram_id = 0 or negative)
  const existingUsers = await supabaseGet<UserRow>(
    'users',
    `select=id,telegram_id,username,first_name&username=eq.${encodeURIComponent(username)}`
  );

  if (existingUsers.length > 0) {
    return existingUsers[0].id;
  }

  // Create new user in users table for web app
  // Use negative telegram_id to distinguish web users from Telegram users
  const newUsers = await supabasePost<UserRow>('users', {
    telegram_id: -Math.abs(username.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)),
    username: username,
    first_name: `${name} ${surname}`,
    countries: [],
    industries: [],
    cities: [],
    is_active: true,
    feedback_metadata: {},
  });

  return newUsers[0].id;
}

export async function login(username: string, password: string): Promise<User | null> {
  try {
    const rows = await supabaseGet<AuthUserRow>(
      'auth_users',
      `select=username,name,surname,password_hash&username=eq.${encodeURIComponent(username)}`
    );

    if (rows.length === 0) {
      console.log('No user found with username:', username);
      return null;
    }

    const row = rows[0];
    if (verifyPassword(password, row.password_hash)) {
      // Get or create user in users table
      const userId = await getOrCreateWebUser(row.username, row.name, row.surname);
      return { 
        id: userId,
        username: row.username, 
        name: row.name, 
        surname: row.surname 
      };
    }

    console.log('Password verification failed');
    return null;
  } catch (error) {
    console.error('Login error:', error);
    return null;
  }
}

export async function signup(username: string, name: string, surname: string, password: string): Promise<User | null> {
  try {
    const passwordHash = hashPassword(password);
    await supabasePost('auth_users', {
      username,
      name,
      surname,
      password_hash: passwordHash,
    });
    
    // Create user in users table
    const userId = await getOrCreateWebUser(username, name, surname);
    return {
      id: userId,
      username,
      name,
      surname,
    };
  } catch (error) {
    console.error('Signup error:', error);
    return null;
  }
}

export async function userExists(username: string): Promise<boolean> {
  try {
    const rows = await supabaseGet<{ username: string }>(
      'auth_users',
      `select=username&username=eq.${encodeURIComponent(username)}`
    );
    return rows.length > 0;
  } catch (error) {
    console.error('User exists check error:', error);
    return false;
  }
}
