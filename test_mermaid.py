import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(dbname='tracker_universitario', user='postgres', password='postgres', host='localhost')
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute('SELECT id, nombre, nivel FROM materias ORDER BY nivel, nombre')
materias = cur.fetchall()

cur.execute('''
    SELECT m.id as materia_id, c.correlativa_id, c.tipo_requisito
    FROM materias m
    JOIN correlativas c ON m.id = c.materia_id
''')
corr = cur.fetchall()

graph = ['graph TD']
for m in materias:
    name = m['nombre'].replace('"', '').replace('(', '').replace(')', '')
    graph.append(f'    M{m["id"]}["{m["id"]}. {name} (Nivel {m["nivel"]})"]')

corr_info = {}
for r in corr:
    m_id = r['materia_id']
    if m_id not in corr_info:
        corr_info[m_id] = {'Regularizada': [], 'Aprobada': []}
    corr_info[m_id][r['tipo_requisito']].append(r['correlativa_id'])

for m_id, reqs in corr_info.items():
    for req in reqs['Regularizada']:
        graph.append(f'    M{req} -.->|Reg| M{m_id}')
    for req in reqs['Aprobada']:
        graph.append(f'    M{req} ==>|Apr| M{m_id}')

with open('mermaid_test.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(graph))
print('Done!')
