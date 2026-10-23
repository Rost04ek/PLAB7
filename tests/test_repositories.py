from datetime import date
from pathlib import Path
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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


def test_crud_user_and_task(session: Session) -> None:
    user_repo = UserRepository(session)
    task_repo = TaskRepository(session)

    user = user_repo.add("ivan_dev")
    assert user.id is not None

    task = task_repo.add(
        Task(
            title="Fix bug #42",
            description="Resolve memory leak",
            priority="high",
            status="todo",
            user_id=user.id,
        )
    )
    assert task.id is not None

    loaded = task_repo.get_by_id(task.id)
    assert loaded is not None
    assert loaded.title == "Fix bug #42"
    assert loaded.user_id == user.id

    updated_status = task_repo.update_status(task.id, "in_progress")
    assert updated_status is not None
    assert updated_status.status == "in_progress"

    updated_prio = task_repo.update_priority(task.id, "low")
    assert updated_prio is not None
    assert updated_prio.priority == "low"

    deleted = task_repo.delete(task.id)
    assert deleted is True
    assert task_repo.get_by_id(task.id) is None


def test_filters_and_search(session: Session) -> None:
    task_repo = TaskRepository(session)
    task_repo.add(Task(title="Write SQL queries", description="DDL and DML", priority="high", status="done"))
    task_repo.add(Task(title="Setup Alembic", description="Database migration", priority="medium", status="todo"))
    task_repo.add(Task(title="Write unit tests", description="Use pytest", priority="high", status="todo"))

    todo_tasks = task_repo.filter_by_status("todo")
    assert len(todo_tasks) == 2

    high_tasks = task_repo.filter_by_priority("high")
    assert len(high_tasks) == 2

    search_results = task_repo.search("alembic")
    assert len(search_results) == 1
    assert search_results[0].title == "Setup Alembic"


def test_status_counts_aggregation(session: Session) -> None:
    task_repo = TaskRepository(session)
    service = TaskService(session)

    task_repo.add(Task(title="T1", description="D1", priority="low", status="done"))
    task_repo.add(Task(title="T2", description="D2", priority="medium", status="done"))
    task_repo.add(Task(title="T3", description="D3", priority="high", status="todo"))
    task_repo.add(Task(title="T4", description="D4", priority="high", status="in_progress"))

    counts = service.get_completion_counts()
    assert counts["completed"] == 2
    assert counts["uncompleted"] == 2

    grouped = service.get_counts_by_status()
    assert grouped["done"] == 2
    assert grouped["todo"] == 1
    assert grouped["in_progress"] == 1


def test_overdue_tasks_query(session: Session) -> None:
    task_repo = TaskRepository(session)
    today = date(2026, 10, 23)

    task_repo.add(
        Task(
            title="Overdue Todo",
            description="Past deadline",
            priority="high",
            status="todo",
            deadline=date(2026, 10, 10),
        )
    )
    task_repo.add(
        Task(
            title="Completed Past",
            description="Already done",
            priority="medium",
            status="done",
            deadline=date(2026, 10, 10),
        )
    )
    task_repo.add(
        Task(
            title="Future Task",
            description="Still have time",
            priority="low",
            status="in_progress",
            deadline=date(2026, 11, 1),
        )
    )

    overdue = task_repo.get_overdue_tasks(reference_date=today)
    assert len(overdue) == 1
    assert overdue[0].title == "Overdue Todo"


def test_batch_transaction_success_and_rollback(session: Session) -> None:
    user_repo = UserRepository(session)
    task_repo = TaskRepository(session)

    u1 = user_repo.add("user_one")
    u2 = user_repo.add("user_two")

    t1 = task_repo.add(Task(title="Task 1", description="...", priority="low", status="todo", user_id=u1.id))
    t2 = task_repo.add(Task(title="Task 2", description="...", priority="medium", status="todo", user_id=u1.id))

    with pytest.raises(ValueError):
        batch_reassign_and_update_status(
            session,
            task_ids=[t1.id, 999999],
            new_user_id=u2.id,
            new_status="in_progress",
        )

    session.refresh(t1)
    assert t1.user_id == u1.id
    assert t1.status == "todo"

    batch_reassign_and_update_status(
        session,
        task_ids=[t1.id, t2.id],
        new_user_id=u2.id,
        new_status="done",
    )
    session.refresh(t1)
    session.refresh(t2)
    assert t1.user_id == u2.id and t1.status == "done"
    assert t2.user_id == u2.id and t2.status == "done"


def test_unique_and_check_constraints(session: Session) -> None:
    user_repo = UserRepository(session)
    user_repo.add("unique_user")

    with pytest.raises(IntegrityError):
        user_repo.add("unique_user")
    session.rollback()

    task_repo = TaskRepository(session)
    with pytest.raises(IntegrityError):
        task_repo.add(Task(title="Bad Priority", description="...", priority="urgent", status="todo"))
    session.rollback()


def test_dbapi_parameterized_filter(tmp_path: Path) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_file = tmp_path / "test_dbapi.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    LocalSession = sessionmaker(bind=engine)

    with LocalSession() as s:
        u = UserRepository(s).add("tester")
        TaskRepository(s).add(
            Task(title="DBAPI Task", description="Test", priority="high", status="todo", user_id=u.id)
        )

    rows = filter_tasks_dbapi(str(db_file), status="todo", priority="high")
    assert len(rows) == 1
    assert rows[0][1] == "DBAPI Task"
    assert rows[0][4] == "tester"
