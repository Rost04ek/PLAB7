from datetime import date, timedelta

from task_manager.database import SessionLocal, engine
from task_manager.models import Base, Task
from task_manager.repositories import (
    TaskRepository,
    UserRepository,
    filter_tasks_dbapi,
)
from task_manager.services import (
    TaskService,
    batch_reassign_and_update_status,
)


def main() -> None:
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        user_repo = UserRepository(session)
        task_repo = TaskRepository(session)
        service = TaskService(session)

        alice = user_repo.get_by_username("alice") or user_repo.add("alice")
        bob = user_repo.get_by_username("bob") or user_repo.add("bob")

        if not task_repo.get_all():
            task_repo.add(
                Task(
                    title="Design DB schema",
                    description="Create tables users and tasks",
                    priority="high",
                    status="done",
                    user_id=alice.id,
                    deadline=date.today() - timedelta(days=2),
                )
            )
            task_repo.add(
                Task(
                    title="Implement Repositories",
                    description="Write CRUD operations with SQLAlchemy",
                    priority="high",
                    status="in_progress",
                    user_id=alice.id,
                    deadline=date.today() - timedelta(days=1),
                )
            )
            task_repo.add(
                Task(
                    title="Write integration tests",
                    description="Cover CRUD and rollback with pytest",
                    priority="medium",
                    status="todo",
                    user_id=bob.id,
                    deadline=date.today() + timedelta(days=3),
                )
            )

        print("=== All Tasks ===")
        for t in task_repo.get_all():
            print(
                f"[{t.id}] {t.title:25} | Priority: {t.priority:6} | "
                f"Status: {t.status:11} | User ID: {t.user_id} | Deadline: {t.deadline}"
            )

        counts = service.get_completion_counts()
        print(
            f"\nCompletion stats -> Done: {counts['completed']}, "
            f"Uncompleted: {counts['uncompleted']}"
        )

        overdue = task_repo.get_overdue_tasks(date.today())
        print("\n=== Overdue Tasks ===")
        for t in overdue:
            print(f"- {t.title} (Deadline was: {t.deadline}, Status: {t.status})")

        dbapi_rows = filter_tasks_dbapi("tasks.db", status="in_progress", priority="high")
        print("\n=== DB-API Filtered (status='in_progress', priority='high') ===")
        for row in dbapi_rows:
            print(row)

        all_tasks = task_repo.get_all()
        if len(all_tasks) >= 2:
            batch_reassign_and_update_status(
                session,
                task_ids=[all_tasks[0].id, all_tasks[1].id],
                new_user_id=bob.id,
                new_status="done",
            )
            print("\nBatch transaction committed successfully!")


if __name__ == "__main__":
    main()
