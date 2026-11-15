from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_activity
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskDeleteResponse,
    TaskResponse,
    TaskStatusEnum,
    TaskUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="1. Crear una nueva tarea para la familia (por el padre)",
    description=(
        "Registra una nueva tarea para la familia recibiendo `name`, `time_granted`, `coins_granted`, "
        "`email_parent`, `description` y `status` (por defecto se asigna `enable` automáticamente). "
        "El campo `created_at` se genera automáticamente en UTC (protegido con JWT)."
    ),
)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    parent_user = db.query(User).filter(User.email_parent == task_in.email_parent.lower()).first()
    if not parent_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró una familia registrada con el correo `email_parent` indicado.",
        )

    if parent_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El `email_parent` enviado no corresponde al usuario autenticado en el token JWT.",
        )

    task = Task(
        name=task_in.name,
        time_granted=task_in.time_granted,
        coins_granted=task_in.coins_granted,
        email_parent=parent_user.email_parent,
        description=task_in.description,
        status=task_in.status.value,
        parent_id=parent_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="CREATE_TASK",
        entity_type="tasks",
        entity_id=task.id,
        details=f"Tarea creada: '{task.name}' (status={task.status}, coins_granted={task.coins_granted})",
    )
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="2. Editar una tarea de la familia (incluyendo habilitar/deshabilitar status)",
    description=(
        "Permite al padre editar cualquier campo de una tarea (`name`, `time_granted`, `coins_granted`, "
        "`description`) e incluso cambiar su `status` entre `enable` y `disable` (protegido con JWT)."
    ),
)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.parent_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna tarea en tu familia con el `task_id` proporcionado.",
        )

    if task_in.name is not None:
        task.name = task_in.name
    if task_in.time_granted is not None:
        task.time_granted = task_in.time_granted
    if task_in.coins_granted is not None:
        task.coins_granted = task_in.coins_granted
    if task_in.description is not None:
        task.description = task_in.description
    if task_in.status is not None:
        task.status = task_in.status.value

    task.updated_at = datetime.now(timezone.utc)
    db.add(task)
    db.commit()
    db.refresh(task)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="UPDATE_TASK",
        entity_type="tasks",
        entity_id=task.id,
        details=f"Tarea actualizada: '{task.name}' (status={task.status}, coins_granted={task.coins_granted})",
    )
    return task


@router.get(
    "",
    response_model=List[TaskResponse],
    summary="3. Listar todas las tareas de una familia (con cualquier estado)",
    description=(
        "Devuelve todas las tareas pertenecientes exclusivamente a la familia del padre autenticado "
        "sin importar su estado (`enable` y `disable`) (protegido con JWT)."
    ),
)
def list_all_family_tasks(
    email_parent: Optional[str] = Query(
        default=None,
        description="Correo del padre (`email_parent`). Opcional ya que se filtra automáticamente por la familia del token JWT.",
        examples=["padre@fhk.app"],
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Task]:
    if email_parent and email_parent.lower() != current_user.email_parent.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El `email_parent` enviado no corresponde al usuario autenticado en el token JWT.",
        )

    return (
        db.query(Task)
        .filter(Task.parent_id == current_user.id)
        .order_by(Task.created_at.desc())
        .all()
    )


@router.get(
    "/enabled",
    response_model=List[TaskResponse],
    summary="4. Listar tareas de una familia solo con estado 'enable'",
    description=(
        "Devuelve únicamente las tareas habilitadas (`status = 'enable'`) pertenecientes a la familia "
        "del padre autenticado (protegido con JWT)."
    ),
)
def list_enabled_family_tasks(
    email_parent: Optional[str] = Query(
        default=None,
        description="Correo del padre (`email_parent`). Opcional ya que se filtra automáticamente por la familia del token JWT.",
        examples=["padre@fhk.app"],
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Task]:
    if email_parent and email_parent.lower() != current_user.email_parent.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El `email_parent` enviado no corresponde al usuario autenticado en el token JWT.",
        )

    return (
        db.query(Task)
        .filter(
            Task.parent_id == current_user.id,
            Task.status == TaskStatusEnum.ENABLE.value,
        )
        .order_by(Task.created_at.desc())
        .all()
    )


@router.delete(
    "/{task_id}",
    response_model=TaskDeleteResponse,
    summary="5. Eliminar una tarea de una familia",
    description=(
        "Elimina permanentemente una tarea de la base de datos buscando por `task_id` y verificando "
        "que pertenezca a la familia del padre autenticado (protegido con JWT)."
    ),
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDeleteResponse:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.parent_id == current_user.id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna tarea en tu familia con el `task_id` proporcionado.",
        )

    deleted_task_name = task.name
    db.delete(task)
    db.commit()

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="DELETE_TASK",
        entity_type="tasks",
        entity_id=task_id,
        details=f"Tarea eliminada: '{deleted_task_name}'",
    )

    return TaskDeleteResponse(
        message="Tarea eliminada correctamente.",
        task_id=task_id,
    )
