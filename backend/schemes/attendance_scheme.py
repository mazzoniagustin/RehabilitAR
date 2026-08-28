from pydantic import BaseModel, EmailStr, field_validator


class AttendanceByEmail(BaseModel):
    token: str
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr):
        return value.lower().strip()