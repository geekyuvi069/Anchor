from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Todo(BaseModel):
    id: int
    title: str
    completed: bool

@app.post("/todos/")
async def create_todo(todo: Todo):
    return {"id": todo.id, "title": todo.title, "completed": todo.completed}

@app.get("/todos/{id}")
async def read_todo(id: int):
    return {"id": id, "title": "Example Title", "completed": False}

@app.put("/todos/{id}")
async def update_todo(id: int, todo: Todo):
    return {"id": id, "title": todo.title, "completed": todo.completed}

@app.delete("/todos/{id}")
async def delete_todo(id: int):
    return {"message": f"Todo with ID {id} deleted"}