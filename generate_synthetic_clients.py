import random
import json
from datetime import datetime, timedelta

random.seed(42)

NUM = 1000
OUT_FILE = 'synthetic_clients.json'
GEN_DATE = datetime.now().strftime('%Y%m%d')

first_names = [
    'Juan', 'Carlos', 'Andrés', 'Diego', 'Jorge', 'Luis', 'Miguel', 'David', 'Felipe', 'Sergio',
    'María', 'Luisa', 'Catalina', 'Andrea', 'Laura', 'Diana', 'Paola', 'Verónica', 'Mónica', 'Carolina'
]
last_names = [
    'Gómez', 'Rodríguez', 'García', 'Martínez', 'López', 'Pérez', 'Sánchez', 'Ramírez', 'Cruz', 'Torres',
    'Hernández', 'Castillo', 'Vargas', 'Morales', 'Rojas'
]

company_domains = [
    'banco.com.co', 'empresa.com.co', 'corp.com.co', 'finanzas.com.co', 'servicios.com.co'
]

cities_other = ['Barranquilla','Cartagena','Cúcuta','Bucaramanga','Pereira','Manizales','Ibagué','Santa Marta']

# Profile buckets counts according to distribution
counts = {
    'Excelente': int(NUM * 0.20),
    'Bueno': int(NUM * 0.40),
    'Regular': int(NUM * 0.30),
    'Malo': NUM - (int(NUM * 0.20) + int(NUM * 0.40) + int(NUM * 0.30))
}

# Build profile list
profiles = []
for k, v in counts.items():
    profiles += [k] * v
random.shuffle(profiles)

# Generate unique cedulas (10 dígitos)
cedulas = random.sample(range(10**9, 10**10), NUM)

# Utilities
def random_birthdate():
    # pick a birthdate between 1960-01-01 and 2000-12-31 but ensure age 24-64 as of today
    while True:
        year = random.randint(1960, 2000)
        month = random.randint(1,12)
        day = random.randint(1,28)
        bd = datetime(year, month, day)
        age = (datetime.now() - bd).days // 365
        if 24 <= age <= 64:
            return bd.strftime('%Y-%m-%d'), age


def choose_city():
    r = random.random()
    if r < 0.40:
        return 'Bogotá'
    elif r < 0.60:
        return 'Medellín'
    elif r < 0.75:
        return 'Cali'
    else:
        return random.choice(cities_other)

# Email uniqueness
used_emails = set()

def make_email(first, last, idx):
    base = f"{first.lower()}.{last.lower()}"
    domain = random.choice(company_domains)
    email = f"{base}@{domain}"
    if email in used_emails:
        email = f"{base}{idx}@{domain}"
    used_emails.add(email)
    return email

# Phone generator
def make_phone():
    # +57 3XX XXX XXXX
    rest = ''.join(str(random.randint(0,9)) for _ in range(9))
    num = '3' + rest
    return f"+57 {num[0:3]} {num[3:6]} {num[6:10]}"

clients = []
used_cedulas = set()
used_ids = set()

for i in range(NUM):
    profile = profiles[i]

    # identity
    ced = cedulas[i]
    used_cedulas.add(ced)

    first = random.choice(first_names)
    last = random.choice(last_names)
    nombre = f"{first} {last}"

    email = make_email(first, last, i+1)
    telefono = make_phone()

    fecha_nac, age = random_birthdate()

    ciudad = choose_city()

    ingreso = random.randint(1500000, 20000000)

    # tipo de empleo
    r = random.random()
    if r < 0.70:
        tipo = 'Empleado'
    elif r < 0.90:
        tipo = 'Independiente'
    else:
        tipo = 'Pensionado'

    max_ant = max(0, min(30, age - 18))
    antiguedad = random.randint(0, max_ant) if max_ant > 0 else 0

    # historialCrediticio consistent with profile
    historial = profile

    # score ranges per profile
    if profile == 'Excelente':
        score = random.randint(750, 850)
        deuda_pct = random.uniform(0.0, 0.20)
    elif profile == 'Bueno':
        score = random.randint(650, 749)
        deuda_pct = random.uniform(0.20, 0.40)
    elif profile == 'Regular':
        score = random.randint(550, 649)
        deuda_pct = random.uniform(0.40, 0.60)
    else:
        score = random.randint(300, 549)
        deuda_pct = random.uniform(0.60, 0.80)

    deuda = int(min(deuda_pct * ingreso, 0.8 * ingreso))

    # saldoCuentaAhorros: distribution by profile
    if profile == 'Excelente':
        saldo = random.randint(5000000, 50000000)
    elif profile == 'Bueno':
        saldo = random.randint(1000000, 20000000)
    elif profile == 'Regular':
        saldo = random.randint(0, 5000000)
    else:
        saldo = random.randint(0, 2000000)

    # id
    seq = str(i+1).zfill(4)
    cid = f"CLT-{GEN_DATE}-{seq}"

    client = {
        'id': cid,
        'cedulaCiudadania': str(ced),
        'nombreCompleto': nombre,
        'email': email,
        'telefono': telefono,
        'fechaNacimiento': fecha_nac,
        'ciudadResidencia': ciudad,
        'ingresoMensual': ingreso,
        'tipoEmpleo': tipo,
        'antiguedadLaboral': antiguedad,
        'historialCrediticio': historial,
        'deudaActual': deuda,
        'saldoCuentaAhorros': saldo,
        'scoreCrediticio': score
    }

    clients.append(client)

# Basic validations
# unique emails
assert len(used_emails) == NUM, f"Emails no únicos: {NUM - len(used_emails)} duplicates"
# unique cedulas
assert len(used_cedulas) == NUM

# distribution check (counts by profile)
from collections import Counter
cnt = Counter([c['historialCrediticio'] for c in clients])
print('Distribution:', cnt)

# write file
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(clients, f, ensure_ascii=False, indent=2)

print(f'Wrote {NUM} clients to {OUT_FILE}')
