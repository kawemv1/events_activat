import os

import psycopg2
from dotenv import load_dotenv


def main() -> None:
    # Load environment variables from .env in project root
    load_dotenv()

    # Try DATABASE_URL first, then fall back to individual parameters
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    try:
        if DATABASE_URL:
            # Try connecting with DATABASE_URL
            connection = psycopg2.connect(DATABASE_URL)
        else:
            # Fall back to individual parameters
            USER = os.getenv("user")
            PASSWORD = os.getenv("password")
            HOST = os.getenv("host")
            PORT = os.getenv("port")
            DBNAME = os.getenv("dbname")
            
            connection = psycopg2.connect(
                user=USER,
                password=PASSWORD,
                host=HOST,
                port=PORT,
                dbname=DBNAME,
            )
        
        print("Connection successful!")

        cursor = connection.cursor()
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        print("Current Time:", result)

        cursor.close()
        connection.close()
        print("Connection closed.")
    except Exception as e:
        print(f"Failed to connect: {e}")


if __name__ == "__main__":
    main()

