"""PostgreSQL schema. Changes are applied with Alembic, never create_all at startup."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Perfil(Base):
    __tablename__ = "perfiles"
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    sexo_registrado: Mapped[str | None] = mapped_column(String(30))
    actividad: Mapped[str] = mapped_column(String(20), server_default="baja")
    preferencia: Mapped[str] = mapped_column(String(20), server_default="balanced")
    __table_args__ = (
        CheckConstraint("actividad IN ('baja', 'media', 'alta')", name="ck_perfiles_actividad"),
        CheckConstraint("preferencia IN ('balanced', 'vegetarian')", name="ck_perfiles_preferencia"),
    )


class Medicion(Base):
    __tablename__ = "mediciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    estatura_cm: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    registrada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        CheckConstraint("peso_kg > 0", name="ck_mediciones_peso_positivo"),
        CheckConstraint("estatura_cm > 0", name="ck_mediciones_estatura_positiva"),
    )


class Plan(Base):
    __tablename__ = "planes"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(100))
    preferencia: Mapped[str] = mapped_column(String(20))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    comidas: Mapped[list["Comida"]] = relationship(cascade="all, delete-orphan", passive_deletes=True, order_by="Comida.id")
    __table_args__ = (
        CheckConstraint("preferencia IN ('balanced', 'vegetarian')", name="ck_planes_preferencia"),
    )


class Comida(Base):
    __tablename__ = "comidas"
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("planes.id", ondelete="CASCADE"), index=True)
    dia: Mapped[int] = mapped_column(Integer)
    momento: Mapped[str] = mapped_column(String(20))
    titulo: Mapped[str] = mapped_column(String(200))
    completada: Mapped[bool] = mapped_column(Boolean, server_default="false")
    __table_args__ = (
        CheckConstraint("dia BETWEEN 0 AND 6", name="ck_comidas_dia"),
        CheckConstraint("momento IN ('desayuno', 'almuerzo', 'cena')", name="ck_comidas_momento"),
        UniqueConstraint("plan_id", "dia", "momento", name="uq_comidas_plan_dia_momento"),
    )


class LoginLimit(Base):
    """Shared fixed-window counter, consistent across Gunicorn workers."""
    __tablename__ = "login_limits"
    clave: Mapped[str] = mapped_column(String(64), primary_key=True)
    intentos: Mapped[int] = mapped_column(Integer)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
