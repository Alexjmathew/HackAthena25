from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017')
db = client['MINI_PROJECT1']
users_collection = db['ALEX']

# Sample data
sample_users = [
    {
        "username": "ALEX J MATHEW",
        "password": "admin123",
        "age": 30,
        "height": 180,
        "weight": 75,
        "blood_group": "O+",
        "sessions": [
            {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "count": 10,
                "total_time": 25.5,
                "average_speed": 2.55
            },
            {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "count": 15,
                "total_time": 30.0,
                "average_speed": 2.0
            }
        ]
    },
    {
        "username": "john_doe",
        "password": "john123",
        "age": 25,
        "height": 175,
        "weight": 70,
        "blood_group": "A+",
        "sessions": [
            {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "count": 20,
                "total_time": 40.0,
                "average_speed": 2.0
            }
        ]
    },
    {
        "username": "jane_smith",
        "password": "jane123",
        "age": 28,
        "height": 160,
        "weight": 60,
        "blood_group": "B+",
        "sessions": [
            {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "count": 12,
                "total_time": 24.0,
                "average_speed": 2.0
            }
        ]
    }
]

# Insert sample data into the collection
users_collection.insert_many(sample_users)

print("Sample data inserted into MongoDB.")
