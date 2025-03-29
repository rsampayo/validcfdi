import os
import sys
import subprocess
import getpass

def create_postgres_db():
    """
    Script to help create a PostgreSQL database and user for the CFDI API
    """
    print("=== PostgreSQL Setup for CFDI API ===")
    
    # Get database details
    db_name = input("Enter database name [cfdi_api]: ") or "cfdi_api"
    db_user = input("Enter database user [cfdi_user]: ") or "cfdi_user"
    db_password = getpass.getpass("Enter database password: ")
    db_host = input("Enter database host [localhost]: ") or "localhost"
    db_port = input("Enter database port [5432]: ") or "5432"
    
    # Commands to create database and user
    commands = [
        f"CREATE USER {db_user} WITH PASSWORD '{db_password}';",
        f"CREATE DATABASE {db_name} OWNER {db_user};",
        f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};"
    ]
    
    # Print SQL commands for manual execution if preferred
    print("\nSQL commands to execute:")
    for cmd in commands:
        print(f"    {cmd}")
    
    # Attempt to execute commands if psql is available
    try_auto = input("\nAttempt to execute these commands automatically? (y/n): ").lower() == 'y'
    
    if try_auto:
        try:
            # Check if psql is available
            subprocess.run(['which', 'psql'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Execute commands
            for cmd in commands:
                subprocess.run(['psql', '-U', 'postgres', '-c', cmd], check=True)
            
            print("\nDatabase and user created successfully!")
        except subprocess.CalledProcessError:
            print("\nCould not execute commands automatically. Please run the SQL commands manually.")
    
    # Create .env file
    create_env = input("\nCreate/update .env file with database settings? (y/n): ").lower() == 'y'
    
    if create_env:
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        # Check if .env exists
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                env_content = f.read()
            
            # Update DATABASE_URL if it exists
            if "DATABASE_URL=" in env_content:
                lines = env_content.splitlines()
                for i, line in enumerate(lines):
                    if line.startswith("DATABASE_URL="):
                        lines[i] = f"DATABASE_URL={db_url}"
                env_content = "\n".join(lines)
            else:
                env_content += f"\nDATABASE_URL={db_url}"
                
            with open(".env", "w") as f:
                f.write(env_content)
        else:
            # Create new .env file
            with open(".env", "w") as f:
                f.write(f"DATABASE_URL={db_url}\n")
                f.write("SECRET_KEY=supersecretkey123456789\n")
        
        print("\n.env file updated!")
    
    print("\nPostgreSQL configuration complete!")
    print(f"Connection string: postgresql://{db_user}:[PASSWORD]@{db_host}:{db_port}/{db_name}")

if __name__ == "__main__":
    create_postgres_db() 