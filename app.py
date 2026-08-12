import os
from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env si existe
load_dotenv()

app = Flask(__name__)

# Configuración de base de datos PostgreSQL desde variables de entorno con fallbacks
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "tracker_universitario")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos PostgreSQL."""
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

@app.route("/")
def index():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            
            # 1. Progreso: Calcular estadísticas de la carrera
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN estado = 'Aprobada' THEN 1 END) as aprobadas,
                    COUNT(CASE WHEN estado = 'Regular' THEN 1 END) as regulares,
                    COUNT(CASE WHEN estado = 'Pendiente' THEN 1 END) as pendientes
                FROM materias;
            """)
            stats = cur.fetchone()
            
            total = stats['total'] or 0
            aprobadas = stats['aprobadas'] or 0
            regulares = stats['regulares'] or 0
            pendientes = stats['pendientes'] or 0
            
            progreso = round((aprobadas * 100.0) / total, 1) if total > 0 else 0.0

            # 2. Plan de Estudios: Obtener todas las materias ordenadas por nivel y nombre (incluyendo nota_final y veces_cursada)
            cur.execute("""
                SELECT id, nombre, nivel, estado, nota_final, veces_cursada
                FROM materias 
                ORDER BY nivel, nombre;
            """)
            materias_all = cur.fetchall()

            # Agrupar materias por nivel (año de la carrera)
            plan_estudios = {}
            for m in materias_all:
                nivel = m['nivel']
                if nivel not in plan_estudios:
                    plan_estudios[nivel] = []
                plan_estudios[nivel].append(m)

            # Calcular promedios por nivel y general
            promedios_por_nivel = {}
            for nivel, materias in plan_estudios.items():
                aprobadas_con_nota = [m for m in materias if m['estado'] == 'Aprobada' and m['nota_final'] is not None]
                if aprobadas_con_nota:
                    promedios_por_nivel[nivel] = round(sum(m['nota_final'] for m in aprobadas_con_nota) / len(aprobadas_con_nota), 2)
                else:
                    promedios_por_nivel[nivel] = None

            todas_aprobadas_con_nota = [m for m in materias_all if m['estado'] == 'Aprobada' and m['nota_final'] is not None]
            promedio_general = round(sum(m['nota_final'] for m in todas_aprobadas_con_nota) / len(todas_aprobadas_con_nota), 2) if todas_aprobadas_con_nota else 0.0

            # 3. Materias Habilitadas para Cursar:
            # Estado 'Pendiente' y que no tengan correlativas de tipo 'Regularizada' sin cumplir (que no estén regularizadas o aprobadas)
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel
                FROM materias m
                WHERE m.estado = 'Pendiente'
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM correlativas c
                      JOIN materias corr ON c.correlativa_id = corr.id
                      WHERE c.materia_id = m.id
                        AND c.tipo_requisito = 'Regularizada'
                        AND corr.estado NOT IN ('Regular', 'Aprobada')
                  )
                ORDER BY m.nivel, m.nombre;
            """)
            materias_habilitadas_cursar = cur.fetchall()

            # 4. Materias Habilitadas para Rendir Examen Final:
            # Estado 'Regular' y que no tengan correlativas de tipo 'Aprobada' sin cumplir (que no estén aprobadas)
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel
                FROM materias m
                WHERE m.estado = 'Regular'
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM correlativas c
                      JOIN materias corr ON c.correlativa_id = corr.id
                      WHERE c.materia_id = m.id
                        AND c.tipo_requisito = 'Aprobada'
                        AND corr.estado <> 'Aprobada'
                  )
                ORDER BY m.nivel, m.nombre;
            """)
            materias_habilitadas_rendir = cur.fetchall()

            # 4. Obtener listado de correlativas para cada materia para poder mostrarlas en la UI
            cur.execute("""
                SELECT 
                    c.materia_id, 
                    c.correlativa_id, 
                    c.tipo_requisito, 
                    corr.nombre as correlativa_nombre,
                    corr.nivel as correlativa_nivel,
                    corr.estado as correlativa_estado
                FROM correlativas c
                JOIN materias corr ON c.correlativa_id = corr.id
                ORDER BY c.materia_id, c.tipo_requisito, corr.nivel, corr.nombre;
            """)
            correlativas_rows = cur.fetchall()

            # Estructurar la información de las correlativas
            correlativas_info = {}
            for r in correlativas_rows:
                m_id = r['materia_id']
                if m_id not in correlativas_info:
                    correlativas_info[m_id] = {'Regularizada': [], 'Aprobada': []}
                
                correlativas_info[m_id][r['tipo_requisito']].append({
                    'id': r['correlativa_id'],
                    'nombre': r['correlativa_nombre'],
                    'nivel': r['correlativa_nivel'],
                    'estado': r['correlativa_estado']
                })

            # 5. Obtener parciales programados con fecha formateada en ISO para JS
            cur.execute("""
                SELECT p.id, p.materia_id, p.nombre, to_char(p.fecha, 'YYYY-MM-DD"T"HH24:MI:SS') as fecha_iso, p.descripcion, m.nombre as materia_nombre, m.nivel as materia_nivel
                FROM parciales p
                JOIN materias m ON p.materia_id = m.id
                ORDER BY p.fecha ASC;
            """)
            parciales = cur.fetchall()

            # 6. Obtener las materias disponibles para rendir/cursar parciales (excluyendo aprobadas y no habilitadas)
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel, m.estado
                FROM materias m
                WHERE m.estado <> 'Aprobada'
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM correlativas c
                      JOIN materias corr ON c.correlativa_id = corr.id
                      WHERE c.materia_id = m.id
                        AND c.tipo_requisito = 'Regularizada'
                        AND corr.estado NOT IN ('Regular', 'Aprobada')
                  )
                ORDER BY m.nivel, m.nombre;
            """)
            materias_disponibles_agenda = cur.fetchall()

            # 7. Obtener los horarios de cursada registrados
            cur.execute("""
                SELECT h.id, h.materia_id, h.dia_semana, to_char(h.hora_inicio, 'HH24:MI') as hora_inicio, to_char(h.hora_fin, 'HH24:MI') as hora_fin, h.aula_comision, m.nombre as materia_nombre, m.nivel as materia_nivel
                FROM horarios_cursada h
                JOIN materias m ON h.materia_id = m.id
                ORDER BY h.dia_semana, h.hora_inicio;
            """)
            horarios_cursada_raw = cur.fetchall()

            horarios_cursada = []
            for r in horarios_cursada_raw:
                horarios_cursada.append(dict(r))

            for i in range(len(horarios_cursada) - 1):
                current = horarios_cursada[i]
                next_item = horarios_cursada[i+1]
                
                if current['dia_semana'] == next_item['dia_semana']:
                    if current['hora_fin'] and next_item['hora_inicio']:
                        curr_hf_h, curr_hf_m = map(int, current['hora_fin'].split(':'))
                        next_hi_h, next_hi_m = map(int, next_item['hora_inicio'].split(':'))
                        
                        diff_mins = (next_hi_h * 60 + next_hi_m) - (curr_hf_h * 60 + curr_hf_m)
                        if diff_mins > 0:
                            dh = diff_mins // 60
                            dm = diff_mins % 60
                            if dh > 0 and dm > 0:
                                current['tiempo_muerto'] = f"{dh}h {dm}m"
                            elif dh > 0:
                                current['tiempo_muerto'] = f"{dh}h"
                            else:
                                current['tiempo_muerto'] = f"{dm}m"


            # Calcular total de horas de cursada
            total_minutos_cursada = 0
            for h in horarios_cursada:
                h_i = h['hora_inicio']
                h_f = h['hora_fin']
                if h_i and h_f:
                    hi_h, hi_m = map(int, h_i.split(':'))
                    hf_h, hf_m = map(int, h_f.split(':'))
                    total_minutos_cursada += (hf_h * 60 + hf_m) - (hi_h * 60 + hi_m)
            
            total_horas_cursada = total_minutos_cursada // 60
            total_minutos_restantes = total_minutos_cursada % 60
            if total_horas_cursada > 0 or total_minutos_restantes > 0:
                tiempo_total_cursada_str = f"{total_horas_cursada}h {total_minutos_restantes}m" if total_minutos_restantes else f"{total_horas_cursada}h"
            else:
                tiempo_total_cursada_str = "0h"

        return render_template(
            "index.html",
            progreso=progreso,
            total_materias=total,
            aprobadas=aprobadas,
            regulares=regulares,
            pendientes=pendientes,
            plan_estudios=plan_estudios,
            materias_habilitadas_cursar=materias_habilitadas_cursar,
            materias_habilitadas_rendir=materias_habilitadas_rendir,
            correlativas_info=correlativas_info,
            promedios_por_nivel=promedios_por_nivel,
            promedio_general=promedio_general,
            parciales=parciales,
            materias_all=materias_all,
            materias_disponibles_agenda=materias_disponibles_agenda,
            horarios_cursada=horarios_cursada,
            tiempo_total_cursada_str=tiempo_total_cursada_str
        )
        
    except psycopg2.OperationalError as e:
        # En caso de error de conexión a la BD, mostramos una UI de error descriptiva
        return render_template("error.html", error_message=str(e), config={
            "host": DB_HOST,
            "database": DB_NAME,
            "user": DB_USER,
            "port": DB_PORT
        })
    finally:
        if conn:
            conn.close()

@app.route("/update-estado", methods=["POST"])
def update_estado():
    """Ruta API para actualizar dinámicamente el estado de una materia y devolver el resultado."""
    data = request.get_json()
    if not data or 'materia_id' not in data or 'nuevo_estado' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos o inválidos."}), 400
    
    materia_id = data['materia_id']
    nuevo_estado = data['nuevo_estado']
    
    if nuevo_estado not in ['Pendiente', 'Regular', 'Aprobada']:
        return jsonify({"success": False, "message": f"Estado '{nuevo_estado}' no es válido."}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Actualizar el estado de la materia y reiniciar nota si no está aprobada
            if nuevo_estado != 'Aprobada':
                cur.execute("""
                    UPDATE materias 
                    SET estado = %s, nota_final = NULL 
                    WHERE id = %s;
                """, (nuevo_estado, materia_id))
            else:
                cur.execute("""
                    UPDATE materias 
                    SET estado = %s 
                    WHERE id = %s;
                """, (nuevo_estado, materia_id))
            conn.commit()
            
        return jsonify({"success": True, "message": f"Estado de la materia {materia_id} actualizado a '{nuevo_estado}'."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al actualizar base de datos: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/update-nota", methods=["POST"])
def update_nota():
    """Ruta API para actualizar dinámicamente la nota de una materia aprobada."""
    data = request.get_json()
    if not data or 'materia_id' not in data or 'nota' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos."}), 400
    
    materia_id = data['materia_id']
    nota = data['nota']
    
    if nota is not None and nota != "":
        try:
            nota = int(nota)
            if nota < 1 or nota > 10:
                return jsonify({"success": False, "message": "La nota debe estar entre 1 y 10."}), 400
        except ValueError:
            return jsonify({"success": False, "message": "La nota debe ser un número entero válido."}), 400
    else:
        nota = None
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Solo permitir actualizar nota si el estado es 'Aprobada'
            cur.execute("""
                UPDATE materias 
                SET nota_final = %s 
                WHERE id = %s AND estado = 'Aprobada';
            """, (nota, materia_id))
            conn.commit()
            
        return jsonify({"success": True, "message": f"Nota de la materia {materia_id} actualizada a {nota if nota else 'NULL'}."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al actualizar nota: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/update-veces-cursada", methods=["POST"])
def update_veces_cursada():
    """Ruta API para actualizar dinámicamente el contador de veces cursada de una materia."""
    data = request.get_json()
    if not data or 'materia_id' not in data or 'veces_cursada' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos."}), 400
    
    materia_id = data['materia_id']
    try:
        veces_cursada = int(data['veces_cursada'])
        if veces_cursada < 0:
            return jsonify({"success": False, "message": "El contador no puede ser menor a 0."}), 400
    except ValueError:
        return jsonify({"success": False, "message": "El contador debe ser un número entero válido."}), 400
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE materias 
                SET veces_cursada = %s 
                WHERE id = %s;
            """, (veces_cursada, materia_id))
            conn.commit()
            
        return jsonify({"success": True, "message": f"Contador de veces cursada actualizado a {veces_cursada}."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al actualizar el contador: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/add-parcial", methods=["POST"])
def add_parcial():
    """Ruta API para agregar un nuevo parcial a la agenda."""
    data = request.get_json()
    if not data or 'materia_id' not in data or 'nombre' not in data or 'fecha' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos."}), 400
    
    materia_id = data['materia_id']
    nombre = data['nombre']
    fecha_str = data['fecha']  # Formato 'YYYY-MM-DDTHH:MM' desde input datetime-local
    descripcion = data.get('descripcion', '')
    
    if not nombre.strip():
        return jsonify({"success": False, "message": "El nombre del parcial no puede estar vacío."}), 400
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO parciales (materia_id, nombre, fecha, descripcion)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (materia_id, nombre, fecha_str, descripcion))
            parcial_id = cur.fetchone()[0]
            conn.commit()
            
        return jsonify({
            "success": True, 
            "message": "Parcial agregado correctamente.",
            "parcial_id": parcial_id
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al guardar el parcial: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/delete-parcial", methods=["POST"])
def delete_parcial():
    """Ruta API para eliminar un parcial de la agenda."""
    data = request.get_json()
    if not data or 'parcial_id' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos."}), 400
    
    parcial_id = data['parcial_id']
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM parciales WHERE id = %s;", (parcial_id,))
            conn.commit()
            
        return jsonify({"success": True, "message": "Parcial eliminado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al eliminar el parcial: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/edit-parcial", methods=["POST"])
def edit_parcial():
    """Ruta API para editar un parcial existente en la agenda."""
    data = request.get_json()
    if not data or 'parcial_id' not in data or 'materia_id' not in data or 'nombre' not in data or 'fecha' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos."}), 400
    
    parcial_id = data['parcial_id']
    materia_id = data['materia_id']
    nombre = data['nombre']
    fecha_str = data['fecha']  # Formato 'YYYY-MM-DDTHH:MM' desde input datetime-local
    descripcion = data.get('descripcion', '')
    
    if not nombre.strip():
        return jsonify({"success": False, "message": "El nombre del parcial no puede estar vacío."}), 400
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE parciales 
                SET materia_id = %s, nombre = %s, fecha = %s, descripcion = %s 
                WHERE id = %s;
            """, (materia_id, nombre, fecha_str, descripcion, parcial_id))
            conn.commit()
            
        return jsonify({"success": True, "message": "Parcial actualizado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al actualizar el parcial: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/add-horario", methods=["POST"])
def add_horario():
    """Ruta API para agregar un nuevo horario de cursada."""
    data = request.get_json()
    if not data or 'materia_id' not in data or 'dia_semana' not in data or 'hora_inicio' not in data or 'hora_fin' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos."}), 400
    
    materia_id = data['materia_id']
    try:
        dia_semana = int(data['dia_semana'])
        if dia_semana < 1 or dia_semana > 6:
            return jsonify({"success": False, "message": "Día de la semana no válido (debe ser entre Lunes=1 y Sábado=6)."}), 400
    except ValueError:
        return jsonify({"success": False, "message": "El día de la semana debe ser un número entero."}), 400

    hora_inicio = data['hora_inicio']
    hora_fin = data['hora_fin']
    aula_comision = data.get('aula_comision', '')
    
    if hora_fin <= hora_inicio:
        return jsonify({"success": False, "message": "La hora de fin debe ser posterior a la hora de inicio."}), 400
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO horarios_cursada (materia_id, dia_semana, hora_inicio, hora_fin, aula_comision)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
            """, (materia_id, dia_semana, hora_inicio, hora_fin, aula_comision))
            horario_id = cur.fetchone()[0]
            conn.commit()
            
        return jsonify({
            "success": True, 
            "message": "Horario de cursada agregado correctamente.",
            "horario_id": horario_id
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al guardar el horario: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/edit-horario", methods=["POST"])
def edit_horario():
    """Ruta API para editar un horario de cursada existente."""
    data = request.get_json()
    if not data or 'horario_id' not in data or 'materia_id' not in data or 'dia_semana' not in data or 'hora_inicio' not in data or 'hora_fin' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos."}), 400
    
    horario_id = data['horario_id']
    materia_id = data['materia_id']
    try:
        dia_semana = int(data['dia_semana'])
        if dia_semana < 1 or dia_semana > 6:
            return jsonify({"success": False, "message": "Día de la semana no válido."}), 400
    except ValueError:
        return jsonify({"success": False, "message": "El día de la semana debe ser un número entero."}), 400

    hora_inicio = data['hora_inicio']
    hora_fin = data['hora_fin']
    aula_comision = data.get('aula_comision', '')
    
    if hora_fin <= hora_inicio:
        return jsonify({"success": False, "message": "La hora de fin debe ser posterior a la hora de inicio."}), 400
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE horarios_cursada 
                SET materia_id = %s, dia_semana = %s, hora_inicio = %s, hora_fin = %s, aula_comision = %s 
                WHERE id = %s;
            """, (materia_id, dia_semana, hora_inicio, hora_fin, aula_comision, horario_id))
            conn.commit()
            
        return jsonify({"success": True, "message": "Horario actualizado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al actualizar el horario: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/delete-horario", methods=["POST"])
def delete_horario():
    """Ruta API para eliminar un horario de cursada."""
    data = request.get_json()
    if not data or 'horario_id' not in data:
        return jsonify({"success": False, "message": "Datos de petición incompletos."}), 400
    
    horario_id = data['horario_id']
    
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM horarios_cursada WHERE id = %s;", (horario_id,))
            conn.commit()
            
        return jsonify({"success": True, "message": "Horario eliminado correctamente."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al eliminar el horario: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

