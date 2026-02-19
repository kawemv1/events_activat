import initSqlJs, { Database } from 'sql.js';

let dbInstance: Database | null = null;

export async function initDatabase(): Promise<Database> {
  if (dbInstance) {
    return dbInstance;
  }

  try {
    console.log('Initializing sql.js...');
    // Use local wasm file from public directory
    const SQL = await initSqlJs({
      locateFile: (file: string) => {
        console.log('Locating file:', file);
        // Serve WASM file from public directory
        if (file.endsWith('.wasm')) {
          return `/${file}`;
        }
        // Fallback to CDN for other files if needed
        return `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`;
      }
    });
    console.log('sql.js initialized successfully');

    // Fetch the database file
    console.log('Fetching database file from /events_bot.db...');
    const response = await fetch('/events_bot.db');
    if (!response.ok) {
      throw new Error(`Failed to fetch database: ${response.status} ${response.statusText}`);
    }
    console.log('Database file fetched, size:', response.headers.get('content-length'));
    const buffer = await response.arrayBuffer();
    const uint8Array = new Uint8Array(buffer);
    console.log('Creating database instance from buffer...');
    
    dbInstance = new SQL.Database(uint8Array);
    console.log('Database instance created successfully');
    return dbInstance;
  } catch (error) {
    console.error('Error initializing database:', error);
    throw error;
  }
}

export interface DatabaseEvent {
  id: number;
  name: string | null;
  title: string;
  description: string | null;
  city: string | null;
  country: string | null;
  start_date: string | null;
  end_date: string | null;
  url: string;
  source: string | null;
  industry: string | null;
  place: string | null;
  image_url: string | null;
}

export async function loadEvents(): Promise<DatabaseEvent[]> {
  try {
    const db = await initDatabase();
    console.log('Database initialized, executing query...');
    
    // Simple query - sql.js might not support NULLS LAST syntax
    const result = db.exec(`
      SELECT id, name, title, description, city, country, start_date, end_date, url, source, industry, place, image_url 
      FROM events 
      ORDER BY start_date DESC
    `);
    
    console.log(`Query returned ${result.length} result sets`);
    
    if (!result || result.length === 0) {
      console.warn('No results returned from database query');
      return [];
    }

    const firstResult = result[0];
    
    if (!firstResult) {
      console.warn('First result is undefined');
      return [];
    }

    // sql.js uses 'lc' for column names (lowercase column names)
    // TypeScript types might not include it, so we access it with bracket notation
    const columns = firstResult['lc'] || firstResult.columns;
    const values = firstResult.values;
    
    if (!columns) {
      console.error('Columns is undefined. Available keys:', Object.keys(firstResult));
      return [];
    }
    
    if (!Array.isArray(columns)) {
      console.error('Columns is not an array:', columns);
      return [];
    }
    
    if (!values) {
      console.error('Values is undefined');
      return [];
    }
    
    if (!Array.isArray(values)) {
      console.error('Values is not an array:', values);
      return [];
    }
    
    console.log(`Found ${values.length} rows, columns:`, columns);

    const events = values.map((row: any[]) => {
      if (!row || !Array.isArray(row)) {
        return null;
      }
      
      const event: any = {};
      columns.forEach((col: string, index: number) => {
        event[col] = row[index] !== null && row[index] !== undefined ? row[index] : null;
      });
      return event as DatabaseEvent;
    }).filter((event): event is DatabaseEvent => event !== null);
    
    console.log(`Parsed ${events.length} events`);
    if (events.length > 0) {
      console.log('Sample event:', events[0]);
    }
    return events;
  } catch (error) {
    console.error('Error in loadEvents:', error);
    throw error;
  }
}
