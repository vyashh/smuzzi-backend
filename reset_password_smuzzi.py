# scripts/reset_pw_sqlite.py
import os, sqlite3
os.environ["PASSLIB_BCRYPT_BACKEND"] = "bcrypt"

from auth import hash_password

USERNAME = "vyash"
NEW_PASSWORD = "HsLeiden2025!"

hashed = hash_password(NEW_PASSWORD)
con = sqlite3.connect("smuzzi.db")
cur = con.cursor()
cur.execute("UPDATE users SET password_hash=? WHERE username=?", (hashed, USERNAME))
con.commit()
print("OK")
