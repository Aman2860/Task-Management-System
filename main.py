from fastapi import FastAPI, Depends, HTTPException, UploadFile, File 
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import uuid
from fastapi.responses import FileResponse

from database import engine, Base, get_db
from models import User, Team, TeamMember, Project, Task, Comment, Attachment
from schemas import UserCreate, LoginSchema, TeamCreate, TeamMemberCreate, ProjectCreate, TaskCreate, CommentCreate, RoleUpdate, AssignTask, UserResponse, TaskStatusUpdate      


Base.metadata.create_all(bind=engine)

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Hash password function
def hash_password(password: str):

    return pwd_context.hash(password)

def create_access_token(data: dict):

    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return token

def get_current_user(token: str = Depends(oauth2_scheme)):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("user_id")
        role = payload.get("role")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return{
            "user_id": user_id,
            "role": role
        }

    except JWTError:
        raise HTTPException(status_code=401,detail="Invalid token")

def admin_required(current_user = Depends(get_current_user)):

    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user

@app.get("/")
def home():
    return {"message": "Task Management API Running"}

@app.get("/users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db), current_user = Depends(admin_required)):
    users = db.query(User).all()
    return users

@app.get("/users/{user_id}")
def get_user_by_id(user_id:int, db:Session=Depends(get_db), current_user=Depends(admin_required)):

    user=db.query(User).filter(User.id==user_id).first()

    if not user:
        raise HTTPException( status_code=404, detail="User not found")
    
    return user

@app.delete("/users/{user_id")
def delete_user(user_id:int, db:Session=Depends(get_db), current_user=Depends(admin_required)):

    user=db.query(User).filter(User.id==user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {
        "message":"User deleted successfully"
    }

@app.put("/users/{user_id}/role")
def update_user_role(user_id: int, role_data: RoleUpdate, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException( status_code=404, detail="User not found")

    user.role = role_data.role
    db.commit()
    db.refresh(user)

    return {
        "message": "Role updated successfully",
        "user_id": user.id,
        "new_role": user.role
    }

@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    
     # Hash user password
    hashed_password = hash_password(user.password)

    # Create user object
    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,
        role="client"
    )

    # Add user to database
    db.add(new_user)
    # Save changes
    db.commit()
    # Refresh object
    db.refresh(new_user)

    return {
        "message": "User created successfully",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email
        }
    }

@app.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == form_data.username).first()

    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    password_correct = pwd_context.verify(form_data.password, existing_user.password)

    if not password_correct:
        raise HTTPException(status_code=401, detail="Incorrect password")

    access_token = create_access_token(
        {
            "user_id": existing_user.id,
            "role": existing_user.role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return current_user

@app.post("/teams")
def create_team(team: TeamCreate,db: Session = Depends(get_db), current_user = Depends(admin_required)):

    new_team = Team(name=team.name, description=team.description)

    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    return {
        "message": "Team created successfully",
        "team": {
            "id": new_team.id,
            "name": new_team.name
        }
    }

@app.get("/teams")
def get_teams(db: Session = Depends(get_db)):

    teams = db.query(Team).all()

    return teams

@app.get("/teams/{team_id}")
def get_team_by_id(team_id: int, db: Session = Depends(get_db)):

    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )
    return team

@app.put("/teams/{team_id}")
def update_team(team_id: int, team: TeamCreate, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    existing_team = db.query(Team).filter(Team.id == team_id).first()

    if not existing_team:

        raise HTTPException(
            status_code=404,
            detail="Team not found")

    existing_team.name = team.name
    existing_team.description = team.description

    db.commit()

    db.refresh(existing_team)

    return existing_team

@app.delete("/teams/{team_id}")
def delete_team(team_id: int, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    team = db.query(Team).filter(Team.id == team_id).first()

    if not team:

        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    db.delete(team)
    db.commit()

    return {
        "message": "Team deleted successfully"
    }

@app.post("/team-members")
def add_member(member: TeamMemberCreate, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    new_member = TeamMember(team_id=member.team_id, user_id=member.user_id)

    db.add(new_member)

    db.commit()

    db.refresh(new_member)

    return {
        "message": "Member added successfully"
    }

@app.get("/teams/{team_id}/members")
def get_team_members(team_id: int, db: Session = Depends(get_db)):

    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    return members

@app.post("/projects")
def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    new_project = Project(name = project.name, description = project.description, team_id = project.team_id)

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "message": "Project created successfully",
        "project": new_project
    }

@app.get("/projects")
def get_projects(db: Session = Depends(get_db)):

    projects = db.query(Project).all()
    return projects

@app.get("/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.put("/projects/{project_id}")
def update_project(project_id: int, project: ProjectCreate, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    existing_project = db.query(Project).filter(Project.id == project_id).first()

    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing_project.name = project.name
    existing_project.description = project.description
    existing_project.team_id = project.team_id

    db.commit()

    db.refresh(existing_project)

    return existing_project

@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)

    db.commit()

    return {
        "message": "Project deleted"
    }

@app.post("/tasks")
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    new_task = Task(
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        project_id=task.project_id,
        assigned_to=task.assigned_to,
        created_by=current_user["user_id"]
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return {
        "message": "Task created successfully",
        "task": new_task
    }

@app.put("/tasks/{task_id}/status")
def update_task_status(task_id: int, status_data: TaskStatusUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException( status_code=404, detail="Task not found")

    allowed_status = ["Pending", "In Progress", "Completed"]

    if status_data.status not in allowed_status:
        raise HTTPException(status_code=400, detail="Invalid status")

    task.status = status_data.status

    db.commit()
    db.refresh(task)

    return task

@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):

    tasks = db.query(Task).all()

    return tasks

@app.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task

@app.get("/my-tasks")
def my_tasks(current_user = Depends(get_current_user), db: Session = Depends(get_db)):

    tasks = db.query(Task).filter(Task.assigned_to == current_user["user_id"]).all()

    return tasks

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task: TaskCreate, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    existing_task = db.query(Task).filter(Task.id == task_id).first()

    if not existing_task:
        raise HTTPException(status_code=404, detail="Task not found")

    existing_task.title = task.title
    existing_task.description = task.description
    existing_task.status = task.status
    existing_task.priority = task.priority
    existing_task.project_id = task.project_id
    existing_task.assigned_to = task.assigned_to
    existing_task.created_by = task.created_by

    db.commit()
    db.refresh(existing_task)

    return existing_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    return {
        "message": "Task deleted"
    }

@app.put("/tasks/{task_id}/assign")
def assign_task(task_id: int, data: AssignTask, db: Session = Depends(get_db), current_user = Depends(admin_required)):

    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    user = db.query(User).filter(User.id == data.user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    task.assigned_to = data.user_id

    db.commit()
    db.refresh(task)

    return {
        "message": "Task assigned successfully",
        "task_id": task.id,
        "assigned_to": task.assigned_to
    }

@app.post("/comments")
def create_comment(comment: CommentCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):

    new_comment = Comment(content=comment.content, task_id=comment.task_id, user_id=current_user["user_id"])

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)

    return {
        "message": "Comment added successfully",
        "comment": new_comment
    }

@app.get("/comments")
def get_comments(db: Session = Depends(get_db)):

    comments = db.query(Comment).all()

    return comments

@app.get("/tasks/{task_id}/comments")
def get_task_comments(task_id: int, db: Session = Depends(get_db)):

    comments = db.query(Comment).filter(Comment.task_id == task_id).all()

    return comments

@app.put("/comments/{comment_id}")
def update_comment(comment_id: int, comment: CommentCreate, db: Session = Depends(get_db)):

    existing_comment = db.query(Comment).filter(Comment.id == comment_id).first()

    if not existing_comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    existing_comment.content = comment.content

    db.commit()
    db.refresh(existing_comment)

    return existing_comment

@app.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db)):

    comment = db.query(Comment).filter(Comment.id == comment_id).first()

    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    db.delete(comment)
    db.commit()

    return {
        "message": "Comment deleted"
    }

@app.post("/attachments")
def upload_file(task_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),  current_user = Depends(get_current_user)):

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_location = f"uploads/{unique_filename}"

    with open(file_location, "wb") as buffer:
        buffer.write(file.file.read())

    attachment = Attachment(filename=unique_filename, task_id=task_id, uploaded_by=current_user["user_id"])

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "message": "File uploaded successfully",
        "file": file.filename
    }

@app.get("/attachments")
def get_attachments(db: Session = Depends(get_db)):

    attachments = db.query(Attachment).all()

    return attachments

@app.get("/tasks/{task_id}/attachments")
def get_task_attachments(task_id: int, db: Session = Depends(get_db)):

    attachments = db.query(Attachment).filter(Attachment.task_id == task_id).all()
    return attachments

@app.get("/attachments/{attachment_id}/download")
def download_file(attachment_id:int, db:Session=Depends(get_db)):

    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = f"uploads/{attachment.filename}"

    return FileResponse(path=file_path, filename=attachment.filename)

@app.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):

    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    db.delete(attachment)
    db.commit()

    return {
        "message": "Attachment deleted"
    }

@app.get("/admin/dashboard")
def admin_dashboard(db:Session=Depends(get_db), current_user=Depends(admin_required)):

    total_users=db.query(User).count()
    total_teams=db.query(Team).count()
    total_projects=db.query(Project).count()
    total_tasks=db.query(Task).count()

    return {
        "total_users":total_users,
        "total_teams":total_teams,
        "total_projects":total_projects,
        "total_tasks":total_tasks
    }

@app.get("/client/dashboard")
def client_dashboard(current_user=Depends(get_current_user), db:Session=Depends(get_db)):

    my_tasks = db.query(Task).filter(Task.assigned_to==current_user["user_id"]).count()

    my_comments=db.query(Comment).filter(Comment.user_id==current_user["user_id"]).count()

    return {
        "my_tasks":my_tasks,
        "my_comments":my_comments
    }