from sqlalchemy import func, select
from sqlalchemy.orm import Session

from task_manager.models import Task, User

VALID_STATUSES = {"todo", "in_progress", "done"}


class TaskService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_completion_counts(self) -> dict[str, int]:
        """Підрахунок кількості виконаних (done) та невиконаних завдань."""
        completed_stmt = select(func.count(Task.id)).where(Task.status == "done")
        uncompleted_stmt = select(func.count(Task.id)).where(Task.status != "done")

        completed = self.session.scalar(completed_stmt) or 0
        uncompleted = self.session.scalar(uncompleted_stmt) or 0

        return {
            "completed": int(completed),
            "uncompleted": int(uncompleted),
        }

    def get_counts_by_status(self) -> dict[str, int]:
        """Агрегація кількості завдань за статусами через GROUP BY."""
        statement = select(Task.status, func.count(Task.id)).group_by(Task.status)
        rows = self.session.execute(statement).all()
        return {status: int(count) for status, count in rows}

    def get_tasks_with_usernames(self) -> list[tuple[str, str, str]]:
        """Приклад JOIN між tasks та users."""
        statement = select(Task.title, Task.status, User.username).join(
            User, Task.user_id == User.id
        )
        rows = self.session.execute(statement).all()
        return [(title, status, username) for title, status, username in rows]


def batch_reassign_and_update_status(
    session: Session,
    task_ids: list[int],
    new_user_id: int,
    new_status: str,
) -> None:
    """
    Транзакційна операція: пакетне перепризначення користувача
    та зміна статусу для списку задач. Якщо будь-яка задача не існує,
    користувач не знайдений або статус некоректний — виконується rollback.
    """
    try:
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")

        user = session.get(User, new_user_id)
        if user is None:
            raise ValueError(f"User with id={new_user_id} not found")

        for task_id in task_ids:
            task = session.get(Task, task_id)
            if task is None:
                raise ValueError(f"Task with id={task_id} not found")

            task.user_id = new_user_id
            task.status = new_status

        session.commit()
    except Exception:
        session.rollback()
        raise
