from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    
class LoginSchema(BaseModel):
    email: str
    password: str

class TeamCreate(BaseModel):
    name: str
    description: str

class TeamMemberCreate(BaseModel):
    team_id: int
    user_id: int

class ProjectCreate(BaseModel):
    name: str
    description: str
    team_id: int

class TaskCreate(BaseModel):
    title: str
    description: str
    status: str
    priority: str
    project_id: int
    assigned_to: int

class CommentCreate(BaseModel):
    content: str
    task_id: int

class RoleUpdate(BaseModel):
    role: str

class AssignTask(BaseModel):
    user_id: int

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

class TaskStatusUpdate(BaseModel):
    status: str