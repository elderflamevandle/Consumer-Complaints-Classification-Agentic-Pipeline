"""Reset admin password and clear failed login count."""
import asyncio, bcrypt, os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

ATLAS    = os.environ["MONGODB_URL"]
DB       = os.environ.get("MONGODB_DB_NAME", "fincomplaint_ai")
EMAIL    = "admin@fincomplaint.ai"
PASSWORD = "Admin1234!"

async def reset():
    client   = AsyncIOMotorClient(ATLAS, serverSelectionTimeoutMS=10_000)
    new_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(12)).decode()
    result   = await client[DB]["users"].update_one(
        {"email": EMAIL},
        {"$set": {
            "password_hash":       new_hash,
            "failed_login_count":  0,
            "locked_until":        None,
            "updated_at":          datetime.now(tz=timezone.utc),
        }},
    )
    print(f"Modified: {result.modified_count}")
    print(f"Login:    {EMAIL}  /  {PASSWORD}")
    client.close()

asyncio.run(reset())
