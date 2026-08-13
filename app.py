import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
from flask_apscheduler import APScheduler
from flask_mail import Mail, Message
import datetime

load_dotenv()


from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super_secret_key_for_eli_cal")

# Tell Flask it is behind a proxy (like Render) to generate https:// URLs for OAuth
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Email Config
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False').lower() in ['true', '1', 't']
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'True').lower() in ['true', '1', 't']
mail = Mail(app)

# Scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "tracker_universitario")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url)
    
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )


@app.route('/login/google')
def login_google():
    # Force HTTPS explicitly for cloud environments behind load balancers
    redirect_uri = url_for('auth_google', _external=True, _scheme='https')
    return google.authorize_redirect(redirect_uri)

@app.route('/login/google/callback')
def auth_google():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            user_info = google.userinfo()
        
        email = user_info.get('email')
        name = user_info.get('name')
        google_id = user_info.get('sub')
        
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, is_admin FROM usuarios WHERE email = %s OR google_id = %s", (email, google_id))
                user = cur.fetchone()
                
                if user:
                    session['user_id'] = user['id']
                    session['username'] = name
                    session['is_admin'] = user.get('is_admin', False)
                    
                    # Update google_id if null
                    cur.execute("UPDATE usuarios SET google_id = %s, email = %s WHERE id = %s", (google_id, email, user['id']))
                else:
                    cur.execute("INSERT INTO usuarios (username, email, google_id) VALUES (%s, %s, %s) RETURNING id", 
                                (name, email, google_id))
                    new_id = cur.fetchone()['id']
                    session['user_id'] = new_id
                    session['username'] = name
                    session['is_admin'] = False
                    

                conn.commit()
                return redirect(url_for('index'))
        finally:
            conn.close()
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error login google: {error_details}")
        return f"<h1>Error Interno de Google Auth</h1><pre>{error_details}</pre>", 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, password_hash, is_admin FROM usuarios WHERE username = %s", (username,))
                user = cur.fetchone()
                
                if user and check_password_hash(user['password_hash'], password):
                    session['user_id'] = user['id']
                    session['username'] = username
                    session['is_admin'] = user['is_admin']
                    return redirect(url_for("index"))
                else:
                    return render_template("login.html", error="Usuario o contraseña incorrectos")
        finally:
            conn.close()
            
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            return render_template("register.html", error="Completa todos los campos")
            
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM usuarios WHERE username = %s", (username,))
                if cur.fetchone():
                    return render_template("register.html", error="El usuario ya existe")
                
                pw_hash = generate_password_hash(password)
                cur.execute("INSERT INTO usuarios (username, password_hash) VALUES (%s, %s) RETURNING id", (username, pw_hash))
                user_id = cur.fetchone()[0]
                conn.commit()
                
                session['user_id'] = user_id
                session['username'] = username
                return redirect(url_for("index"))
        finally:
            conn.close()
            
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/elegir-carrera", methods=["GET", "POST"])
def elegir_carrera():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if request.method == "POST":
                carrera_id = request.form.get("carrera_id")
                if not carrera_id:
                    return redirect(url_for("elegir_carrera"))
                
                # Verify career exists
                cur.execute("SELECT id FROM carreras WHERE id = %s", (carrera_id,))
                if not cur.fetchone():
                    return "Carrera no válida", 400
                    
                user_id = session['user_id']
                
                # Update user with carrera_id
                cur.execute("UPDATE usuarios SET carrera_id = %s WHERE id = %s", (carrera_id, user_id))
                
                # Populate usuario_materias with subjects from this career
                cur.execute("""
                    INSERT INTO usuario_materias (usuario_id, materia_id, estado, nota_final, veces_cursada)
                    SELECT %s, id, 'Pendiente', NULL, 0 FROM materias WHERE carrera_id = %s
                    ON CONFLICT (usuario_id, materia_id) DO NOTHING;
                """, (user_id, carrera_id))
                
                # Sync basic sciences (shared subjects) from previous careers
                cur.execute("""
                    UPDATE usuario_materias um_new
                    SET estado = um_old.estado,
                        nota_final = um_old.nota_final,
                        veces_cursada = um_old.veces_cursada
                    FROM materias m_new, materias m_old, usuario_materias um_old
                    WHERE um_new.usuario_id = %s
                      AND um_old.usuario_id = %s
                      AND um_new.materia_id = m_new.id
                      AND um_old.materia_id = m_old.id
                      AND m_new.carrera_id = %s
                      AND m_old.carrera_id != %s
                      AND m_new.nombre = m_old.nombre
                      AND (um_old.estado != 'Pendiente' OR um_old.veces_cursada > 0);
                """, (user_id, user_id, carrera_id, carrera_id))
                
                conn.commit()
                return redirect(url_for("index"))
                
            cur.execute("SELECT id, nombre FROM carreras ORDER BY id;")
            carreras = cur.fetchall()
            return render_template("elegir_carrera.html", carreras=carreras)
    finally:
        conn.close()

@app.route("/")
def index():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    user_id = session['user_id']
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            
            # Check if user has a career chosen
            cur.execute("SELECT carrera_id, username, is_admin FROM usuarios WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if not user or not user['carrera_id']:
                return redirect(url_for('elegir_carrera'))
                
            session['is_admin'] = user['is_admin']
            session['username'] = user['username']
            
            # 1. Progreso
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN estado = 'Aprobada' THEN 1 END) as aprobadas,
                    COUNT(CASE WHEN estado = 'Regular' THEN 1 END) as regulares,
                    COUNT(CASE WHEN estado = 'Pendiente' THEN 1 END) as pendientes
                FROM usuario_materias
                WHERE usuario_id = %s;
            """, (user_id,))
            stats = cur.fetchone()
            
            total = stats['total'] or 0
            aprobadas = stats['aprobadas'] or 0
            regulares = stats['regulares'] or 0
            pendientes = stats['pendientes'] or 0
            progreso = round((aprobadas * 100.0) / total, 1) if total > 0 else 0.0

            # 2. Plan de Estudios
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel, um.estado, um.nota_final, um.veces_cursada
                FROM materias m
                JOIN usuario_materias um ON m.id = um.materia_id
                WHERE um.usuario_id = %s AND m.carrera_id = %s
                ORDER BY m.nivel, m.nombre;
            """, (user_id, user['carrera_id']))
            materias_all = cur.fetchall()

            plan_estudios = {}
            for m in materias_all:
                nivel = m['nivel']
                if nivel not in plan_estudios:
                    plan_estudios[nivel] = []
                plan_estudios[nivel].append(m)

            promedios_por_nivel = {}
            for nivel, materias in plan_estudios.items():
                aprobadas_con_nota = [m for m in materias if m['estado'] == 'Aprobada' and m['nota_final'] is not None]
                promedios_por_nivel[nivel] = round(sum(m['nota_final'] for m in aprobadas_con_nota) / len(aprobadas_con_nota), 2) if aprobadas_con_nota else None

            todas_aprobadas_con_nota = [m for m in materias_all if m['estado'] == 'Aprobada' and m['nota_final'] is not None]
            promedio_general = round(sum(m['nota_final'] for m in todas_aprobadas_con_nota) / len(todas_aprobadas_con_nota), 2) if todas_aprobadas_con_nota else 0.0

            # 3. Materias Habilitadas para Cursar
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel
                FROM materias m
                JOIN usuario_materias um ON m.id = um.materia_id
                WHERE um.usuario_id = %s AND m.carrera_id = %s AND um.estado = 'Pendiente'
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM correlativas c
                      JOIN usuario_materias corr_um ON c.correlativa_id = corr_um.materia_id
                      WHERE c.materia_id = m.id
                        AND corr_um.usuario_id = %s
                        AND c.tipo_requisito = 'Regularizada'
                        AND corr_um.estado NOT IN ('Regular', 'Aprobada')
                  )
                ORDER BY m.nivel, m.nombre;
            """, (user_id, user['carrera_id'], user_id))
            materias_habilitadas_cursar = cur.fetchall()

            # 4. Materias Habilitadas para Rendir
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel
                FROM materias m
                JOIN usuario_materias um ON m.id = um.materia_id
                WHERE um.usuario_id = %s AND m.carrera_id = %s AND um.estado = 'Regular'
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM correlativas c
                      JOIN usuario_materias corr_um ON c.correlativa_id = corr_um.materia_id
                      WHERE c.materia_id = m.id
                        AND corr_um.usuario_id = %s
                        AND c.tipo_requisito = 'Aprobada'
                        AND corr_um.estado != 'Aprobada'
                  )
                ORDER BY m.nivel, m.nombre;
            """, (user_id, user['carrera_id'], user_id))
            materias_habilitadas_rendir = cur.fetchall()

            # 5. Obtener Correlativas Structuradas (para el mapa)
            cur.execute("""
                SELECT 
                    m.id as materia_id, m.nombre as materia_nombre, m.nivel as materia_nivel, um.estado as materia_estado,
                    c.correlativa_id, c.tipo_requisito,
                    cm.nombre as correlativa_nombre, cum.estado as correlativa_estado
                FROM materias m
                JOIN usuario_materias um ON m.id = um.materia_id AND um.usuario_id = %s
                LEFT JOIN correlativas c ON m.id = c.materia_id
                LEFT JOIN materias cm ON c.correlativa_id = cm.id
                LEFT JOIN usuario_materias cum ON cm.id = cum.materia_id AND cum.usuario_id = %s
                WHERE m.carrera_id = %s
                ORDER BY m.nivel, m.id;
            """, (user_id, user_id, user['carrera_id']))
            correlativas_rows = cur.fetchall()

            correlativas_info = {}
            for r in correlativas_rows:
                m_id = r['materia_id']
                if m_id not in correlativas_info:
                    correlativas_info[m_id] = {'Regularizada': [], 'Aprobada': []}
                
                if r['correlativa_id']:
                    correlativas_info[m_id][r['tipo_requisito']].append({
                        'id': r['correlativa_id'],
                        'nombre': r['correlativa_nombre'],
                        'estado': r['correlativa_estado']
                    })

            # 6. Parciales
            cur.execute("""
                SELECT p.id, p.materia_id, p.nombre, to_char(p.fecha, 'YYYY-MM-DD"T"HH24:MI:SS') as fecha_iso, p.descripcion, m.nombre as materia_nombre, m.nivel as materia_nivel, p.notificar, p.antelacion_dias
                FROM parciales p
                JOIN materias m ON p.materia_id = m.id
                WHERE p.usuario_id = %s
                ORDER BY p.fecha ASC;
            """, (user_id,))
            parciales = cur.fetchall()

            # 6. Materias disponibles agenda
            cur.execute("""
                SELECT m.id, m.nombre, m.nivel, um.estado
                FROM materias m
                JOIN usuario_materias um ON m.id = um.materia_id
                WHERE um.usuario_id = %s AND m.carrera_id = %s AND um.estado <> 'Aprobada'
                  AND NOT EXISTS (
                      SELECT 1 
                      FROM correlativas c
                      JOIN usuario_materias corr_um ON c.correlativa_id = corr_um.materia_id
                      WHERE c.materia_id = m.id
                        AND corr_um.usuario_id = %s
                        AND c.tipo_requisito = 'Regularizada'
                        AND corr_um.estado NOT IN ('Regular', 'Aprobada')
                  )
                ORDER BY m.nivel, m.nombre;
            """, (user_id, user['carrera_id'], user_id))
            materias_disponibles_agenda = cur.fetchall()

            # 7. Horarios cursada
            cur.execute("""
                SELECT h.id, h.materia_id, h.dia_semana, to_char(h.hora_inicio, 'HH24:MI') as hora_inicio, to_char(h.hora_fin, 'HH24:MI') as hora_fin, h.aula_comision, m.nombre as materia_nombre, m.nivel as materia_nivel
                FROM horarios_cursada h
                JOIN materias m ON h.materia_id = m.id
                WHERE h.usuario_id = %s AND m.carrera_id = %s
                ORDER BY h.dia_semana, h.hora_inicio;
            """, (user_id, user['carrera_id']))
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
            
            # 8. Obtener Ranking Global (Top 5)
            cur.execute("""
                SELECT 
                    u.username, 
                    c.nombre as carrera,
                    COUNT(um.materia_id) FILTER (WHERE um.estado = 'Aprobada') as materias_aprobadas,
                    ROUND(AVG(um.nota_final) FILTER (WHERE um.estado = 'Aprobada' AND um.nota_final IS NOT NULL), 2) as promedio,
                    ROUND((COUNT(um.materia_id) FILTER (WHERE um.estado = 'Aprobada') * 100.0) / NULLIF(COUNT(um.materia_id), 0), 1) as avance_porcentaje
                FROM usuarios u
                JOIN carreras c ON u.carrera_id = c.id
                JOIN usuario_materias um ON u.id = um.usuario_id
                GROUP BY u.id, u.username, c.nombre
                ORDER BY materias_aprobadas DESC, promedio DESC
                LIMIT 5;
            """)
            ranking = cur.fetchall()

        return render_template(
            "index.html",
            username=session.get('username'),
            is_admin=session.get('is_admin'),
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
            tiempo_total_cursada_str=tiempo_total_cursada_str,
            ranking=ranking
        )
        
    except psycopg2.OperationalError as e:
        return render_template("error.html", error_message=str(e), config={
            "host": DB_HOST, "database": DB_NAME, "user": DB_USER, "port": DB_PORT
        })
    finally:
        if conn:
            conn.close()

@app.route("/admin")
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for("index"))
        
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    u.id, 
                    u.username,
                    u.created_at,
                    COUNT(um.materia_id) as total_materias,
                    SUM(CASE WHEN um.estado = 'Aprobada' THEN 1 ELSE 0 END) as aprobadas,
                    SUM(CASE WHEN um.estado = 'Regular' THEN 1 ELSE 0 END) as regulares,
                    SUM(CASE WHEN um.estado = 'Pendiente' THEN 1 ELSE 0 END) as pendientes,
                    ROUND(AVG(CASE WHEN um.estado = 'Aprobada' AND um.nota_final IS NOT NULL THEN um.nota_final ELSE NULL END), 2) as promedio_general,
                    COALESCE((SELECT SUM(EXTRACT(EPOCH FROM (h.hora_fin - h.hora_inicio))/3600) FROM horarios_cursada h WHERE h.usuario_id = u.id), 0) as horas_semanales
                FROM usuarios u
                LEFT JOIN usuario_materias um ON u.id = um.usuario_id
                WHERE u.is_admin = FALSE
                GROUP BY u.id
                ORDER BY u.created_at DESC;
            """)
            estudiantes = cur.fetchall()
            
        return render_template("admin.html", estudiantes=estudiantes, username=session.get('username'))
    except psycopg2.OperationalError as e:
        return render_template("error.html", error_message=str(e), config={"host": DB_HOST})
    finally:
        if conn:
            conn.close()

@app.route("/update-estado", methods=["POST"])
def update_estado():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    materia_id = data['materia_id']
    nuevo_estado = data['nuevo_estado']
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if nuevo_estado != 'Aprobada':
                cur.execute("""
                    UPDATE usuario_materias
                    SET estado = %s, nota_final = NULL
                    WHERE usuario_id = %s 
                      AND materia_id IN (
                          SELECT m1.id FROM materias m1 
                          JOIN materias m2 ON m1.nombre = m2.nombre 
                          WHERE m2.id = %s
                      );
                """, (nuevo_estado, user_id, materia_id))
            else:
                cur.execute("""
                    UPDATE usuario_materias
                    SET estado = %s
                    WHERE usuario_id = %s 
                      AND materia_id IN (
                          SELECT m1.id FROM materias m1 
                          JOIN materias m2 ON m1.nombre = m2.nombre 
                          WHERE m2.id = %s
                      );
                """, (nuevo_estado, user_id, materia_id))
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

@app.route("/update-nota", methods=["POST"])
def update_nota():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    materia_id = data['materia_id']
    nota = int(data['nota']) if data['nota'] else None
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE usuario_materias
                SET nota_final = %s
                WHERE usuario_id = %s 
                  AND estado = 'Aprobada'
                  AND materia_id IN (
                      SELECT m1.id FROM materias m1 
                      JOIN materias m2 ON m1.nombre = m2.nombre 
                      WHERE m2.id = %s
                  );
            """, (nota, user_id, materia_id))
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

@app.route("/update-veces-cursada", methods=["POST"])
def update_veces_cursada():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    materia_id = data['materia_id']
    veces = int(data['veces_cursada'])
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE usuario_materias
                SET veces_cursada = %s
                WHERE usuario_id = %s 
                  AND materia_id IN (
                      SELECT m1.id FROM materias m1 
                      JOIN materias m2 ON m1.nombre = m2.nombre 
                      WHERE m2.id = %s
                  );
            """, (veces, user_id, materia_id))
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

@app.route("/add-parcial", methods=["POST"])
def add_parcial():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    
    notificar = bool(data.get('notificar', False))
    antelacion = int(data.get('antelacion_dias', 1))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO parciales (usuario_id, materia_id, nombre, fecha, descripcion, notificar, antelacion_dias) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;", 
                        (user_id, data['materia_id'], data['nombre'], data['fecha'], data.get('descripcion', ''), notificar, antelacion))
            parcial_id = cur.fetchone()[0]
            conn.commit()
        return jsonify({"success": True, "parcial_id": parcial_id})
    finally:
        conn.close()

@app.route("/delete-parcial", methods=["POST"])
def delete_parcial():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM parciales WHERE id = %s AND usuario_id = %s;", (data['parcial_id'], user_id))
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

@app.route("/edit-parcial", methods=["POST"])
def edit_parcial():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    
    notificar = bool(data.get('notificar', False))
    antelacion = int(data.get('antelacion_dias', 1))
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE parciales SET materia_id = %s, nombre = %s, fecha = %s, descripcion = %s, notificar = %s, antelacion_dias = %s WHERE id = %s AND usuario_id = %s;", 
                        (data['materia_id'], data['nombre'], data['fecha'], data.get('descripcion', ''), notificar, antelacion, data['parcial_id'], user_id))
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

@app.route("/add-horario", methods=["POST"])
def add_horario():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO horarios_cursada (usuario_id, materia_id, dia_semana, hora_inicio, hora_fin, aula_comision) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;", 
                        (user_id, data['materia_id'], str(data['dia_semana']), data['hora_inicio'], data['hora_fin'], data.get('aula_comision', '')))
            h_id = cur.fetchone()[0]
            conn.commit()
        return jsonify({"success": True, "horario_id": h_id})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "message": f"Server Error: {str(e)}", "trace": traceback.format_exc()}), 500
    finally:
        conn.close()

@app.route("/edit-horario", methods=["POST"])
def edit_horario():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE horarios_cursada SET materia_id = %s, dia_semana = %s, hora_inicio = %s, hora_fin = %s, aula_comision = %s WHERE id = %s AND usuario_id = %s;", 
                        (data['materia_id'], str(data['dia_semana']), data['hora_inicio'], data['hora_fin'], data.get('aula_comision', ''), data['horario_id'], user_id))
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "message": f"Server Error: {str(e)}", "trace": traceback.format_exc()}), 500
    finally:
        conn.close()

@app.route("/delete-horario", methods=["POST"])
def delete_horario():
    if 'user_id' not in session: return jsonify({"success": False, "message": "No autenticado"}), 401
    user_id = session['user_id']
    data = request.get_json()
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM horarios_cursada WHERE id = %s AND usuario_id = %s;", (data['horario_id'], user_id))
            conn.commit()
        return jsonify({"success": True})
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


@scheduler.task('cron', id='send_reminders', hour=9, minute=0)
def send_reminders():
    with app.app_context():
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                today = datetime.datetime.now().date()
                
                cur.execute('''
                    SELECT p.id, p.fecha, p.nombre as p_nombre, m.nombre as materia_nombre, u.email, u.username, p.antelacion_dias
                    FROM parciales p
                    JOIN materias m ON p.materia_id = m.id
                    JOIN usuarios u ON p.usuario_id = u.id
                    WHERE p.notificar = TRUE 
                      AND DATE(p.fecha) - p.antelacion_dias = %s
                      AND u.email IS NOT NULL
                ''', (today,))
                
                exams = cur.fetchall()
                for exam in exams:
                    if not exam['email']: continue
                    msg = Message(f"Recordatorio de Examen: {exam['materia_nombre']}",
                                  sender=app.config['MAIL_USERNAME'],
                                  recipients=[exam['email']])
                    dias_texto = f"{exam['antelacion_dias']} día{'s' if exam['antelacion_dias'] > 1 else ''}"
                    msg.body = f"Hola {exam['username']},\n\nTienes un examen ('{exam['p_nombre']}') de {exam['materia_nombre']} programado para el {exam['fecha']} (en {dias_texto}).\n\n¡Mucho éxito preparándote!\nEli-Cal Tracker"
                    try:
                        mail.send(msg)
                        print(f"Sent reminder to {exam['email']}")
                    except Exception as e:
                        print(f"Error sending email to {exam['email']}: {e}")
        except Exception as e:
            print(f"Error checking reminders: {e}")
        finally:
            conn.close()
