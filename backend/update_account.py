from app.database import SessionLocal
from app.models import User
from sqlalchemy.orm import Session

def make_account_unlimited(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.subscription_tier = "business"  # Unlimited tier
            user.monthly_usage = 0  # Reset usage
            db.commit()
            print(f"✅ Account {email} updated to business tier (unlimited)")
            print(f"Monthly usage reset to 0")
        else:
            print(f"❌ User with email {email} not found")
    finally:
        db.close()

# Update your account - replace with your actual email
make_account_unlimited("parthbhalodiya24@gmail.com")
