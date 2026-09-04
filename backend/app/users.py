"""Command-line user management, for bootstrapping the first admin.

    python -m app.users add <username> [--admin]
    python -m app.users passwd <username>
    python -m app.users list
"""

from __future__ import annotations

import getpass
import sys

from sqlalchemy import select

from .database import SessionLocal, init_db
from .models import User
from .security import hash_password


def _prompt_password() -> str:
    p1 = getpass.getpass("Password: ")
    p2 = getpass.getpass("Repeat: ")
    if p1 != p2:
        sys.exit("passwords do not match")
    if len(p1) < 6:
        sys.exit("password must be at least 6 characters")
    return p1


def main(argv: list[str]) -> None:
    init_db()
    if not argv:
        sys.exit(__doc__)
    cmd, *rest = argv
    db = SessionLocal()
    try:
        if cmd == "list":
            for u in db.scalars(select(User).order_by(User.username)):
                flags = " ".join(f for f, on in [("admin", u.is_admin), ("disabled", u.disabled)] if on)
                print(f"{u.username:20} {flags}")
        elif cmd == "add":
            if not rest:
                sys.exit("usage: add <username> [--admin]")
            username = rest[0]
            if db.scalar(select(User).where(User.username == username)):
                sys.exit(f"user {username!r} already exists")
            user = User(
                username=username,
                password_hash=hash_password(_prompt_password()),
                is_admin="--admin" in rest,
            )
            db.add(user)
            db.commit()
            print(f"created {username}" + (" (admin)" if user.is_admin else ""))
        elif cmd == "passwd":
            if not rest:
                sys.exit("usage: passwd <username>")
            user = db.scalar(select(User).where(User.username == rest[0]))
            if user is None:
                sys.exit("no such user")
            user.password_hash = hash_password(_prompt_password())
            db.commit()
            print("password updated")
        else:
            sys.exit(__doc__)
    finally:
        db.close()


if __name__ == "__main__":
    main(sys.argv[1:])
