import datetime
import random
from pathlib import Path

OUT_FILE = Path(__file__).with_name('synthetic_transacciones.sql')
NUM_TX = 10000
NUM_ACCOUNTS = 500
START_DATE = datetime.date(2023, 12, 5)
END_DATE = datetime.date(2025, 12, 5)

random.seed(123456789)

accounts = [f"ACC-{i:05d}" for i in range(1, NUM_ACCOUNTS+1)]
num_days = (END_DATE - START_DATE).days + 1

# Distribute transactions across days as evenly as possible
base_per_day = NUM_TX // num_days
remainder = NUM_TX % num_days
per_day_counts = [base_per_day + (1 if d < remainder else 0) for d in range(num_days)]

# Helper: pick account with per-day cap enforcement
PER_ACCOUNT_PER_DAY_CAP = 50

# Prepare writers
lines = []

transaction_id_counters = {}  # date_str -> counter
per_day_account_counts = {}  # date_str -> {account: count}

# Type and channel weights
# tipo_transaccion: TRANSFERENCIA 40%, DEPOSITO 25%, RETIRO 20%, PAGO_SERVICIO 15%
# canal: APP_MOVIL 50%, WEB 30%, CAJERO 15%, SUCURSAL 5%

def pick_tipo(r):
    if r < 0.40:
        return 'TRANSFERENCIA'
    elif r < 0.65:
        return 'DEPOSITO'
    elif r < 0.85:
        return 'RETIRO'
    else:
        return 'PAGO_SERVICIO'


def pick_canal(r):
    if r < 0.50:
        return 'APP_MOVIL'
    elif r < 0.80:
        return 'WEB'
    elif r < 0.95:
        return 'CAJERO'
    else:
        return 'SUCURSAL'


def monto_for(tipo, r):
    if tipo == 'TRANSFERENCIA':
        low, high = 10000, 5000000
    elif tipo == 'DEPOSITO':
        low, high = 20000, 10000000
    elif tipo == 'RETIRO':
        low, high = 10000, 3000000
    else:  # PAGO_SERVICIO
        low, high = 5000, 500000
    return round(low + r * (high - low), 2)


def descripcion_for(tipo, origen, destino=None):
    if tipo == 'TRANSFERENCIA':
        return f"Transferencia de {origen} a {destino}"
    elif tipo == 'DEPOSITO':
        return f"Depósito en cuenta {origen}"
    elif tipo == 'RETIRO':
        return f"Retiro en efectivo desde {origen}"
    else:
        return f"Pago de servicio desde {origen}"

# Generate per-day sequences
tx_total = 0
for day_idx, count in enumerate(per_day_counts):
    current_date = START_DATE + datetime.timedelta(days=day_idx)
    date_str = current_date.strftime('%Y%m%d')
    # initialize counters
    transaction_id_counters[date_str] = 0
    per_day_account_counts[date_str] = {acc: 0 for acc in accounts}

    # generate sorted times within the day
    # we'll space them evenly within 86400 seconds with a small deterministic offset
    for j in range(count):
        transaction_id_counters[date_str] += 1
        seq = transaction_id_counters[date_str]
        # time within day, evenly spaced
        seconds_in_day = int((j + 1) * 86400 / (count + 1))
        # small deterministic micro-offset
        micro_offset = ((j * 97) % 59)
        fecha_hora = datetime.datetime.combine(current_date, datetime.time(0,0,0)) + datetime.timedelta(seconds=seconds_in_day, minutes=micro_offset)
        fecha_hora_str = fecha_hora.strftime('%Y-%m-%d %H:%M:%S')

        # pseudo-random numbers
        r = random.random()
        r2 = random.random()
        r3 = random.random()
        r4 = random.random()
        r5 = random.random()

        tipo = pick_tipo(r)
        canal = pick_canal(r3)
        monto = monto_for(tipo, r4)

        # estado rules: RECHAZADA only for TRANSFERENCIA and RETIRO as 5% each
        estado = 'EXITOSA'
        if tipo in ('TRANSFERENCIA', 'RETIRO'):
            if r2 < 0.05:
                estado = 'RECHAZADA'
            elif r2 < 0.15:
                estado = 'PENDIENTE'
            else:
                estado = 'EXITOSA'
        else:
            if r2 < 0.10:
                estado = 'PENDIENTE'
            else:
                estado = 'EXITOSA'

        # pick origin account respecting per-account per-day cap
        origin_idx = int(r5 * NUM_ACCOUNTS)
        origin = accounts[origin_idx]
        # find an account with available capacity
        attempts = 0
        while per_day_account_counts[date_str][origin] >= PER_ACCOUNT_PER_DAY_CAP and attempts < NUM_ACCOUNTS:
            origin_idx = (origin_idx + 1) % NUM_ACCOUNTS
            origin = accounts[origin_idx]
            attempts += 1
        # fallback (shouldn't happen given caps and distribution)
        if per_day_account_counts[date_str][origin] >= PER_ACCOUNT_PER_DAY_CAP:
            # pick first account with < cap
            for a in accounts:
                if per_day_account_counts[date_str][a] < PER_ACCOUNT_PER_DAY_CAP:
                    origin = a
                    break

        id_cuenta_origen = origin
        id_cuenta_destino = None

        if tipo == 'TRANSFERENCIA':
            # pick destination different and with capacity
            # start from a different pseudo-random index
            dest_idx = (origin_idx + 1 + int(r4 * (NUM_ACCOUNTS-1))) % NUM_ACCOUNTS
            destino = accounts[dest_idx]
            attempts = 0
            while (destino == origin or per_day_account_counts[date_str][destino] >= PER_ACCOUNT_PER_DAY_CAP) and attempts < NUM_ACCOUNTS:
                dest_idx = (dest_idx + 1) % NUM_ACCOUNTS
                destino = accounts[dest_idx]
                attempts += 1
            if destino == origin or per_day_account_counts[date_str][destino] >= PER_ACCOUNT_PER_DAY_CAP:
                # fallback: choose next available
                for a in accounts:
                    if a != origin and per_day_account_counts[date_str][a] < PER_ACCOUNT_PER_DAY_CAP:
                        destino = a
                        break
            id_cuenta_destino = destino
            # increment destination count as well
            per_day_account_counts[date_str][id_cuenta_destino] += 1
        else:
            id_cuenta_destino = None

        # increment origin count
        per_day_account_counts[date_str][id_cuenta_origen] += 1

        # build id_transaccion
        id_transaccion = f"TRX-{date_str}-{seq:05d}"

        # descripcion
        descripcion = descripcion_for(tipo, id_cuenta_origen, id_cuenta_destino)

        # build SQL values (NULL for destination when appropriate)
        destino_sql = 'NULL' if id_cuenta_destino is None else f"'{id_cuenta_destino}'"
        row = (
            f"INSERT INTO transacciones (id_transaccion, fecha_hora, id_cuenta_origen, id_cuenta_destino, tipo_transaccion, monto, estado, canal, descripcion) VALUES ("
            f"'{id_transaccion}', '{fecha_hora_str}', '{id_cuenta_origen}', {destino_sql}, '{tipo}', {monto:.2f}, '{estado}', '{canal}', '{descripcion}');"
        )
        lines.append(row)
        tx_total += 1

# Write to file
OUT_FILE.write_text('\n'.join(lines), encoding='utf-8')
print(f'Wrote {tx_total} INSERTs to {OUT_FILE}')
