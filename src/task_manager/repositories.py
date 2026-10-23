import sqlite3
from datetime import date
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from task_manager.models import Task, User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, username: str) -> User:
        user = User(username=username)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        statement = select(User).where(User.username == username)
        return self.session.scalar(statement)

    def get_all(self) -> list[User]:
        statement = select(User).order_by(User.id)
        return list(self.session.scalars(statement))

    def delete(self, user_id: int) -> bool:
        user = self.get_by_id(user_id)
        if user is None:
            return False
        self.session.delete(user)
        self.session.commit()
        return True


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, task: Task) -> Task:
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def get_by_id(self, task_id: int) -> Task | None:
        return self.session.get(Task, task_id)

    def get_all(self) -> list[Task]:
        statement = select(Task).order_by(Task.id)
        return list(self.session.scalars(statement))

    def update_status(self, task_id: int, new_status: str) -> Task | None:
        task = self.get_by_id(task_id)
        if task is None:
            return None
        task.status = new_status
        self.session.commit()
        self.session.refresh(task)
        return task

    def update_priority(self, task_id: int, new_priority: str) -> Task | None:
        task = self.get_by_id(task_id)
        if task is None:
            return None
        task.priority = new_priority
        self.session.commit()
        self.session.refresh(task)
        return task

    def assign_user(self, task_id: int, user_id: int | None) -> Task | None:
        task = self.get_by_id(task_id)
        if task is None:
            return None
        task.user_id = user_id
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task_id: int) -> bool:
        task = self.get_by_id(task_id)
        if task is None:
            return False
        self.session.delete(task)
        self.session.commit()
        return True

    def filter_by_status(self, status: str) -> list[Task]:
        statement = select(Task).where(Task.status == status)
        return list(self.session.scalars(statement))

    def filter_by_priority(self, priority: str) -> list[Task]:
        statement = select(Task).where(Task.priority == priority)
        return list(self.session.scalars(statement))

    def search(self, query: str) -> list[Task]:
        pattern = f"%{query}%"
        statement = select(Task).where(
            or_(
                Task.title.ilike(pattern),
                Task.description.ilike(pattern),
            )
        )
        return list(self.session.scalars(statement))

    def get_overdue_tasks(self, reference_date: date | None = None) -> list[Task]:
        """Пошук прострочених завдань (дедлайн минув, а статус не 'done')."""
        check_date = reference_date or date.today()
        statement = (
            select(Task)
            .where(
                Task.deadline.is_not(None),
                Task.deadline < check_date,
                Task.status != "done",
            )
            .order_by(Task.deadline.asc())
        )
        return list(self.session.scalars(statement))


def filter_tasks_dbapi(
    database_path: str,
    status: str,
    priority: str,
) -> list[tuple]:
    """
    Демонстрація роботи з Python DB-API (sqlite3) та параметризованим запитом.
    Фільтрація завдань за status та priority із JOIN таблиці users.
    """
    with sqlite3.connect(database_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                tasks.id,
                tasks.title,
                tasks.priority,
                tasks.status,
                users.username
            FROM tasks
            LEFT JOIN users ON tasks.user_id = users.id
            WHERE tasks.status = ? AND tasks.priority = ?
            ORDER BY tasks.id ASC
            """,
            (status, priority),
        )
        return cursor.fetchall()
