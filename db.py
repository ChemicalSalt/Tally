from pymongo import MongoClient
import os

def get_db():
    client = MongoClient(os.environ.get("MONGO_URI"))
    return client["tally"]

def get_or_create_user(google_id, name, email, picture):
    db = get_db()
    users_col = db["users"]
    user = users_col.find_one({"google_id": google_id})
    if not user:
        from models import user_doc
        users_col.insert_one(user_doc(google_id, name, email, picture))
        user = users_col.find_one({"google_id": google_id})
    return user

def save_expense(user_id, amount, category, note, date):
    db = get_db()
    from models import expense_doc
    db["expenses"].insert_one(expense_doc(user_id, amount, category, note, date))

def get_expenses(user_id):
    db = get_db()
    return list(db["expenses"].find(
        {"user_id": user_id},
        sort=[("date", -1)]
    ))

def delete_expense(expense_id):
    from bson import ObjectId
    db = get_db()
    db["expenses"].delete_one({"_id": ObjectId(expense_id)})

def update_budget(user_id, budget):
    db = get_db()
    db["users"].update_one(
        {"google_id": user_id},
        {"$set": {"monthly_budget": float(budget)}}
    )