"""Profile CRUD practice project: FastAPI + Pydantic + SQLAlchemy."""
from contextlib import asynccontextmanager
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import CheckConstraint, String, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DATABASE_PATH = FilePath(__file__).with_name("profile_api.db")
engine = create_engine(f"sqlite:///{DATABASE_PATH}", connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (CheckConstraint("age > 0 AND age < 120", name="valid_age"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(15))
    # Store a normalized key so uniqueness is enforced by the database itself.
    username_key: Mapped[str] = mapped_column(String, unique=True)
    age: Mapped[int]


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=15)
    age: int = Field(gt=0, lt=120)

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value):
        return value.strip() if isinstance(value, str) else value


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str | None = Field(default=None, min_length=3, max_length=15)
    age: int | None = Field(default=None, gt=0, lt=120)

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("Supply at least one field to update")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Supplied fields cannot be null")
        return self


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    age: int


class ProfileList(BaseModel):
    profiles: list[ProfileRead]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


app = FastAPI(title="Profile Management API", version="1.0.0", lifespan=lifespan)


def get_session():
    with Session(engine) as session:
        yield session


DB = Annotated[Session, Depends(get_session)]
ProfileID = Annotated[int, Path(gt=0)]


def find_profile(profile_id: int, session: Session):
    profile = session.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


def save_profile(session: Session, profile: Profile):
    requested_key = profile.username_key
    requested_id = profile.id
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Confirm the cause rather than labeling every integrity error a duplicate.
        conflict = session.scalar(select(Profile).where(Profile.username_key == requested_key))
        if conflict is not None and conflict.id != requested_id:
            raise HTTPException(status_code=409, detail="Username already exists")
        raise
    session.refresh(profile)
    return profile


@app.post("/profiles", response_model=ProfileRead, status_code=201)
def create_profile(data: ProfileCreate, session: DB):
    profile = Profile(username=data.username, username_key=data.username.casefold(), age=data.age)
    session.add(profile)
    return save_profile(session, profile)


@app.get("/profiles", response_model=ProfileList)
def list_profiles(
    session: DB,
    min_age: Annotated[int, Query(ge=0, lt=120)] = 0,
    limit: Annotated[int, Query(gt=0, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    statement = select(Profile).where(Profile.age >= min_age).order_by(Profile.id).offset(offset).limit(limit)
    return {"profiles": session.scalars(statement).all()}


@app.get("/profiles/{profile_id}", response_model=ProfileRead)
def read_profile(profile_id: ProfileID, session: DB):
    return find_profile(profile_id, session)


@app.patch("/profiles/{profile_id}", response_model=ProfileRead)
def update_profile(profile_id: ProfileID, data: ProfileUpdate, session: DB):
    profile = find_profile(profile_id, session)
    for name, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, name, value)
    if "username" in data.model_fields_set:
        profile.username_key = data.username.casefold()
    return save_profile(session, profile)


@app.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: ProfileID, session: DB):
    profile = find_profile(profile_id, session)
    session.delete(profile)
    session.commit()
    return Response(status_code=204)
