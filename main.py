from typing import TypeVar, Generic, Optional, List
from pydantic import BaseModel, Field, EmailStr
from fastapi import FastAPI, HTTPException, status
from datetime import datetime

# ==========================================
# 1. Общие модели (Аналог ErrorResponse и SuccessResponse)
# ==========================================
T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Унифицированный формат успешного ответа (как в Go-проекте)"""

    success: bool = True
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """Формат ответа при ошибке"""

    error: str
    message: str


# ==========================================
# 2. Модели данных User (Аналог internal/models/user.go)
# ==========================================
class User(BaseModel):
    """Модель пользователя для ответа"""

    id: int = Field(..., description="Уникальный идентификатор пользователя")
    email: str = Field(..., description="Электронная почта пользователя")
    name: str = Field(..., description="Имя пользователя")
    created_at: datetime = Field(..., description="Дата и время создания аккаунта")


class CreateUserRequest(BaseModel):
    email: EmailStr = Field(
        ..., description="Email пользователя (обязательно, валидный формат)"
    )
    name: str = Field(
        ...,
        max_length=100,
        description="Имя пользователя (обязательно, макс. 100 символов)",
    )


class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = Field(None, description="Новый email (необязательно)")
    name: Optional[str] = Field(
        None, max_length=100, description="Новое имя (необязательно)"
    )


# ==========================================
# 3. Модели данных Todo (Аналог internal/models/todo.go)
# ==========================================
class Todo(BaseModel):
    """Модель задачи для ответа"""

    id: int = Field(..., description="Уникальный идентификатор задачи")
    user_id: int = Field(
        ..., description="ID пользователя, которому принадлежит задача"
    )
    title: str = Field(..., description="Название задачи")
    description: str = Field(..., description="Описание задачи")
    done: bool = Field(
        ..., description="Статус выполнения (True - выполнено, False - нет)"
    )
    created_at: datetime = Field(..., description="Дата и время создания задачи")
    updated_at: datetime = Field(
        ..., description="Дата и время последнего обновления задачи"
    )


class CreateTodoRequest(BaseModel):
    user_id: int = Field(..., description="ID пользователя (обязательно)")
    title: str = Field(
        ...,
        max_length=200,
        description="Название задачи (обязательно, макс. 200 символов)",
    )
    description: str = Field(
        "",
        max_length=1000,
        description="Описание задачи (необязательно, макс. 1000 символов)",
    )
    done: bool = Field(False, description="Статус выполнения по умолчанию (False)")


class UpdateTodoRequest(BaseModel):
    title: Optional[str] = Field(
        None, max_length=200, description="Новое название задачи"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Новое описание задачи"
    )
    done: Optional[bool] = Field(None, description="Обновленный статус выполнения")


# ==========================================
# 4. Хранилище в памяти (Аналог map[int]models.X в Go)
# ==========================================
users_db: dict[int, User] = {}
todos_db: dict[int, Todo] = {}
next_user_id: int = 1
next_todo_id: int = 1

# ==========================================
# 5. Инициализация приложения (Аналог main.go с chi.NewRouter())
# ==========================================
app = FastAPI(
    title="Todo API Service",
    description="REST API для управления пользователями и задачами. Проект адаптирован с Go (chi + swaggo) на Python (FastAPI + Pydantic) для сохранения учебной цели модуля по работе с ИИ и документацией.",
    version="1.0.0",
)

# ==========================================
# 6. Эндпоинты User (Аналог internal/handlers/user.go)
# ==========================================


@app.get(
    "/api/v1/users/",
    response_model=SuccessResponse[List[User]],
    summary="Получить список всех пользователей",
)
async def list_users():
    return SuccessResponse[List[User]](data=list(users_db.values()))


@app.get(
    "/api/v1/users/{user_id}",
    response_model=SuccessResponse[User],
    summary="Получить пользователя по ID",
)
async def get_user(user_id: int):
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    return SuccessResponse[User](data=user)


@app.post(
    "/api/v1/users/",
    response_model=SuccessResponse[User],
    status_code=status.HTTP_201_CREATED,
    summary="Создать нового пользователя",
)
async def create_user(req: CreateUserRequest):
    global next_user_id
    new_user = User(
        id=next_user_id, email=req.email, name=req.name, created_at=datetime.utcnow()
    )
    users_db[next_user_id] = new_user
    next_user_id += 1
    return SuccessResponse[User](data=new_user)


@app.put(
    "/api/v1/users/{user_id}",
    response_model=SuccessResponse[User],
    summary="Обновить данные пользователя (частично)",
)
async def update_user(user_id: int, req: UpdateUserRequest):
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )

    # Частичное обновление (аналог проверки на nil в Go)
    if req.email is not None:
        user.email = req.email
    if req.name is not None:
        user.name = req.name

    users_db[user_id] = user
    return SuccessResponse[User](data=user)


@app.delete(
    "/api/v1/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить пользователя",
)
async def delete_user(user_id: int):
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден"
        )
    del users_db[user_id]
    return None


# ==========================================
# 7. Эндпоинты Todo (Аналог internal/handlers/todo.go)
# ==========================================


@app.get(
    "/api/v1/todos/",
    response_model=SuccessResponse[List[Todo]],
    summary="Получить список всех задач",
)
async def list_todos():
    return SuccessResponse[List[Todo]](data=list(todos_db.values()))


@app.get(
    "/api/v1/todos/{todo_id}",
    response_model=SuccessResponse[Todo],
    summary="Получить задачу по ID",
)
async def get_todo(todo_id: int):
    todo = todos_db.get(todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена"
        )
    return SuccessResponse[Todo](data=todo)


@app.post(
    "/api/v1/todos/",
    response_model=SuccessResponse[Todo],
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую задачу",
)
async def create_todo(req: CreateTodoRequest):
    global next_todo_id
    new_todo = Todo(
        id=next_todo_id,
        user_id=req.user_id,
        title=req.title,
        description=req.description,
        done=req.done,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    todos_db[next_todo_id] = new_todo
    next_todo_id += 1
    return SuccessResponse[Todo](data=new_todo)


@app.put(
    "/api/v1/todos/{todo_id}",
    response_model=SuccessResponse[Todo],
    summary="Обновить задачу (частично)",
)
async def update_todo(todo_id: int, req: UpdateTodoRequest):
    todo = todos_db.get(todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена"
        )

    # Частичное обновление (аналог проверки на nil в Go)
    if req.title is not None:
        todo.title = req.title
    if req.description is not None:
        todo.description = req.description
    if req.done is not None:
        todo.done = req.done
    todo.updated_at = datetime.utcnow()

    todos_db[todo_id] = todo
    return SuccessResponse[Todo](data=todo)


@app.delete(
    "/api/v1/todos/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить задачу",
)
async def delete_todo(todo_id: int):
    if todo_id not in todos_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена"
        )
    del todos_db[todo_id]
    return None
