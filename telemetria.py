#!/usr/bin/env python3
import sys
import time
import requests

# CONFIGURACIÓN (Cada estudiante/grupo modifica estos valores)
SUPABASE_URL = "https://tkktjvybkfrznbzdlfgo.supabase.co"
SUPABASE_KEY = "sb_publishable_eI3w9vk6jq_MZfaoFVcynQ_dIs-fxiq"
DEVICE_ID    = "[nombre del dispositivo]"
INTERVALO    = 10  # Segundos entre envíos


def leer_temp_soc():
    """Lee la temperatura interna del SoC / CPU."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as archivo:
            return round(float(archivo.read().strip()) / 1000.0, 2)
    except FileNotFoundError:
        return None


def leer_uso_ram():
    """Calcula el porcentaje de memoria RAM en uso desde /proc/meminfo."""
    try:
        with open("/proc/meminfo", "r") as archivo:
            lineas = dict(line.split()[:2] for line in archivo if ":" in line)
            total = float(lineas["MemTotal:"])
            disponible = float(lineas["MemAvailable:"])
            return round(((total - disponible) / total) * 100.0, 1)
    except Exception:
        return None


def enviar_telemetria(temp, ram):
    """Envía la medición de temperatura y RAM a la base de datos de Supabase vía REST."""
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/telemetria_rpi"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    payload = {
        "device_id": DEVICE_ID,
        "temperature": temp,
        "ram_usage": ram
    }
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=5)
        print(f"[{DEVICE_ID}] Temp: {temp}°C | RAM: {ram}% | Estado HTTP: {res.status_code}", flush=True)
        return res.status_code in (200, 201)
    except Exception as e:
        print(f"[{DEVICE_ID}] Error al enviar: {e}", flush=True)
        return False


if __name__ == "__main__":
    temp = leer_temp_soc()
    ram = leer_uso_ram()

    if temp is None:
        print("Error: No se encontró el sensor térmico (/sys/class/thermal/thermal_zone0/temp).")
        sys.exit(1)

    if ram is None:
        ram = 0.0

    # Si se pasa el argumento 'once', se ejecuta una sola vez (para el timer de systemd)
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        enviar_telemetria(temp, ram)
    else:
        # Modo continuo por defecto (para el servicio continuo de systemd)
        print(f"Iniciando demonio continuo para '{DEVICE_ID}' (cada {INTERVALO}s)...", flush=True)
        while True:
            t = leer_temp_soc()
            r = leer_uso_ram()
            if t is not None and r is not None:
                enviar_telemetria(t, r)
            time.sleep(INTERVALO)
