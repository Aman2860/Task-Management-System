from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str
    
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
    created_by: int

class CommentCreate(BaseModel):
    content: str
    task_id: int
    user_id: int