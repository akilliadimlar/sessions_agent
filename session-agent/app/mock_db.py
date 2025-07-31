import json
from pathlib import Path

class MockDB:
    def __init__(self, json_path="mock_sessions.json"):
        self.json_path = Path(__file__).parent / json_path

    async def find_one(self, query):
        # Only supports {"_id": ...} queries for now
        if "_id" not in query:
            return None
        try:
            with self.json_path.open(encoding="utf-8") as f:
                sessions = json.load(f)
            for session in sessions:
                if session.get("_id") == query["_id"]:
                    return session
        except FileNotFoundError:
            print(f"Mock data file not found: {self.json_path}")
            return None
        return None

# Create a mock sessions collection that mimics MongoDB interface
class MockSessions:
    def __init__(self):
        self.mock_db = MockDB()
    
    async def find_one(self, query):
        return await self.mock_db.find_one(query)

# Create a mock database object that mimics the MongoDB db object
class MockDatabase:
    def __init__(self):
        self.sessions = MockSessions()

# Export a mock db instance
mock_db = MockDatabase() 