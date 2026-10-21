from datetime import date, timedelta

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, Conflict, NotFound

from backend.auth import login_required
from backend.database import get_db
from backend.diet_engine import DAYS, build_plan
from backend.models import Comida, Medicion, Perfil, Plan
from backend.validation import body, choice, date_value, decimal_value, text_value

api = Blueprint('api', __name__)


def profile_json(profile):
    if profile is None:
        return None
    today = date.today()
    born = profile.fecha_nacimiento
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return {'fecha_nacimiento': born.isoformat(), 'edad': age,
            'sexo_registrado': profile.sexo_registrado, 'actividad': profile.actividad,
            'preferencia': profile.preferencia}


def measurement_json(row):
    return {'id': row.id, 'peso_kg': str(row.peso_kg), 'estatura_cm': str(row.estatura_cm),
            'registrada_en': row.registrada_en.isoformat()}


def plan_json(row, details=False):
    value = {'id': row.id, 'nombre': row.nombre, 'preferencia': row.preferencia,
             'fecha_inicio': row.fecha_inicio.isoformat(), 'creado_en': row.creado_en.isoformat()}
    if details:
        value['days'] = [
            {'day': name, 'date': (row.fecha_inicio + timedelta(days=index)).isoformat(),
             'meals': [{'id': meal.id, 'label': meal.momento.capitalize(), 'title': meal.titulo,
                        'completed': meal.completada}
                       for meal in row.comidas if meal.dia == index]}
            for index, name in enumerate(DAYS)
        ]
    return value


@api.get('/api/profile')
@login_required
def profile():
    return jsonify(profile=profile_json(get_db().get(Perfil, g.user.id)))


@api.post('/api/profile')
@login_required
def save_profile():
    data = body()
    born = date_value(data, 'fecha_nacimiento')
    if not date(1900, 1, 1) <= born <= date.today():
        raise BadRequest('La fecha de nacimiento debe estar entre 1900 y hoy.')
    activity = choice(data, 'actividad', ('baja', 'media', 'alta'))
    preference = choice(data, 'preferencia', ('balanced', 'vegetarian'))
    sex = choice(data, 'sexo_registrado', (None, 'femenino', 'masculino', 'intersexual', 'no_indicado'))
    db = get_db()
    # Upsert prevents duplicate profiles when requests arrive concurrently.
    from sqlalchemy.dialects.postgresql import insert
    values = dict(usuario_id=g.user.id, fecha_nacimiento=born, actividad=activity,
                  preferencia=preference, sexo_registrado=sex)
    statement = insert(Perfil).values(**values)
    db.execute(statement.on_conflict_do_update(index_elements=[Perfil.usuario_id], set_=values))
    db.commit()
    db.expire_all()
    return jsonify(profile=profile_json(db.get(Perfil, g.user.id)))


@api.get('/api/measurements')
@login_required
def measurements():
    db = get_db()
    try:
        page = max(1, int(request.args.get('page', '1')))
    except ValueError:
        raise BadRequest('La página debe ser un número entero.') from None
    total = db.scalar(select(func.count()).select_from(Medicion).where(Medicion.usuario_id == g.user.id))
    rows = db.scalars(select(Medicion).where(Medicion.usuario_id == g.user.id)
                      .order_by(Medicion.registrada_en.desc(), Medicion.id.desc()).offset((page - 1) * 20).limit(20))
    return jsonify(measurements=[measurement_json(row) for row in rows], total=total, page=page, page_size=20)


@api.post('/api/measurements')
@login_required
def add_measurement():
    data = body()
    row = Medicion(usuario_id=g.user.id,
                   peso_kg=decimal_value(data, 'peso_kg', '9999.99'),
                   estatura_cm=decimal_value(data, 'estatura_cm', '999.99'))
    db = get_db()
    db.add(row)
    db.commit()
    return jsonify(measurement=measurement_json(row)), 201


@api.delete('/api/measurements/<int:measurement_id>')
@login_required
def delete_measurement(measurement_id):
    db = get_db()
    row = db.scalar(select(Medicion).where(Medicion.id == measurement_id, Medicion.usuario_id == g.user.id))
    if row is None:
        raise NotFound('Medición no encontrada.')
    db.delete(row)
    db.commit()
    return '', 204


@api.get('/api/plans')
@login_required
def plans():
    db = get_db()
    try:
        page = max(1, int(request.args.get('page', '1')))
    except ValueError:
        raise BadRequest('La página debe ser un número entero.') from None
    total = db.scalar(select(func.count()).select_from(Plan).where(Plan.usuario_id == g.user.id))
    rows = db.scalars(select(Plan).where(Plan.usuario_id == g.user.id)
                      .order_by(Plan.id.desc()).offset((page - 1) * 10).limit(10))
    return jsonify(plans=[plan_json(row) for row in rows], total=total, page=page, page_size=10)


def owned_plan(plan_id):
    row = get_db().scalar(select(Plan).options(selectinload(Plan.comidas)).where(
        Plan.id == plan_id, Plan.usuario_id == g.user.id))
    if row is None:
        raise NotFound('Plan no encontrado.')
    return row


@api.post('/api/plans')
@login_required
def create_plan():
    data = body()
    db = get_db()
    profile = db.get(Perfil, g.user.id)
    if profile is None:
        raise Conflict('Guarda tu perfil antes de crear un menú.')
    start = date_value(data, 'fecha_inicio')
    if not date(1900, 1, 1) <= start <= date(2100, 12, 31):
        raise BadRequest('La fecha de inicio debe estar entre 1900 y 2100.')
    if start.weekday() != 0:
        raise BadRequest('Elige un lunes como inicio del menú semanal.')
    name = text_value(data, 'nombre', 2, 100)
    plan = Plan(usuario_id=g.user.id, nombre=name, preferencia=profile.preferencia, fecha_inicio=start)
    for index, day in enumerate(build_plan(profile.preferencia)):
        for meal in day['meals']:
            plan.comidas.append(Comida(dia=index, momento=meal['label'].lower(), titulo=meal['title']))
    db.add(plan)
    db.commit()
    return jsonify(plan=plan_json(plan, True)), 201


@api.get('/api/plans/latest')
@login_required
def latest_plan():
    row = get_db().scalar(select(Plan).options(selectinload(Plan.comidas)).where(
        Plan.usuario_id == g.user.id).order_by(Plan.id.desc()).limit(1))
    return jsonify(plan=plan_json(row, True) if row else None)


@api.get('/api/plans/<int:plan_id>')
@login_required
def get_plan(plan_id):
    return jsonify(plan=plan_json(owned_plan(plan_id), True))


@api.delete('/api/plans/<int:plan_id>')
@login_required
def delete_plan(plan_id):
    db = get_db()
    db.delete(owned_plan(plan_id))
    db.commit()
    return '', 204


@api.patch('/api/plans/<int:plan_id>/meals/<int:meal_id>')
@login_required
def update_meal(plan_id, meal_id):
    data = body()
    completed = data.get('completed')
    if not isinstance(completed, bool):
        raise BadRequest('completed debe ser true o false.')
    plan = owned_plan(plan_id)
    meal = next((item for item in plan.comidas if item.id == meal_id), None)
    if meal is None:
        raise NotFound('Comida no encontrada.')
    meal.completada = completed
    get_db().commit()
    return jsonify(id=meal.id, completed=meal.completada)
