from src.database import session, UserSettings


def fetch_email(user_id: str) -> str | None:
    entry = session.query(UserSettings).filter_by(user_id=user_id).first()
    return entry.email if entry else None


def store_email(user_id: str, email: str) -> None:
    entry = UserSettings(user_id=user_id, email=email)
    session.merge(entry)
    session.commit()
