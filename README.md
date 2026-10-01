# Taller Demonios & Systemd
### Pontificia Universidad Javeriana
**Departamento de Ingeniería Electrónica**  
**Asignatura:** Sistemas Embebidos  

**Autores:**  
- **Andrés Felipe Jiménez Albor** ([andresf.jimeneza@javeriana.edu.co](mailto:andresf.jimeneza@javeriana.edu.co))  
- **Daniel Santiago Caicedo Guzman** ([caicedo-ds@javeriana.edu.co](mailto:caicedo-ds@javeriana.edu.co))  

---

## Fundamentos teóricos

### ¿Qué es un demonio en Linux?
En los sistemas operativos tipo Unix, un demonio es un proceso que se ejecuta en segundo plano (*background*), sin estar vinculado a una terminal de control interactiva (`/dev/tty`). Los demonios se encargan de brindar servicios del sistema, atender peticiones de red o monitorear sensores de hardware.

Tradicionalmente, en Unix un proceso se convertía en demonio ejecutando una secuencia llamada *doble fork* (`fork()` -> `setsid()` -> `fork()`), cerrando los descriptores de archivo estándar (`stdin`, `stdout`, `stderr`) y redirigiéndolos a `/dev/null`, quedando adoptado por el proceso inicial del sistema (`PID 1`).

En los sistemas modernos basados en Systemd, ya no es necesario implementar complejas rutinas de doble fork en el código fuente: **Systemd se encarga de aislar, demonizar, supervisar y contener el proceso mediante cgroups de Linux.**

---

### Estructura de una unidad Systemd (`.service`)
En systemd, cada recurso gestionado se denomina **Unit** y se describe mediante un archivo declarativo con sintaxis tipo INI. Las unidades más relevantes para este taller son:

* **`.service`**: Describe cómo iniciar, supervisar y detener un proceso o demonio.
* **`.timer`**: Funciona como un cronómetro de eventos que activa un `.service` homónimo cuando se cumple una condición temporal. Reemplaza y amplía las capacidades de cron.
* **`.target`**: Puntos de sincronización o estados de ejecución (equivalentes modernos a los runlevels de SysVinit, ej. `multi-user.target`).

Las rutas de configuración prioritarias en el sistema de archivos son:
* `/etc/systemd/system/`: Unidades creadas o modificadas por el administrador (tienen máxima prioridad sobre las predeterminadas).
* `/lib/systemd/system/` (o `/usr/lib/...`): Unidades provistas por los paquetes instalados por el sistema operativo.

---

### Anatomía de una Unidad `.service`
Un archivo de servicio contiene típicamente tres secciones obligatorias o sugeridas:

```ini
[Unit]
Description=Nombre descriptivo del servicio
After=network.target            # Iniciar sólo después de que la red esté activa
Wants=network-online.target     # Dependencia suave

[Service]
Type=simple                     # simple, forking, oneshot, notify
User=pi                         # Usuario que ejecuta el proceso (principio de menor privilegio)
WorkingDirectory=/home/pi/app
ExecStart=/usr/bin/python3 /home/pi/app/main.py
Restart=on-failure              # Reinicio automático si el proceso cae inesperadamente
RestartSec=5s

[Install]
WantedBy=multi-user.target      # Target en el que se habilita al arrancar
```

#### Tipos de Servicio (`Type=`)
* **`simple`** (por defecto): El proceso indicado en `ExecStart` es el servicio principal.
* **`oneshot`**: El proceso ejecuta una tarea finita y termina (ideal para tareas periódicas llamadas por un `.timer`).
* **`forking`**: Adecuado para binarios heredados que hacen `fork()` internamente y devuelven el control a la terminal.

---

### Anatomía de una Unidad `.timer`
Un `.timer` coordina la ejecución de un archivo `.service` del mismo nombre (por ejemplo, `telemetria.timer` dispara a `telemetria-timer.service`).

```ini
[Unit]
Description=Disparador periódico de telemetría

[Timer]
OnBootSec=1min                  # Temporizador monotónico: 1 min tras el encendido
OnUnitActiveSec=30s             # Cada 30 s desde la última activación
# Alternativa basada en calendario (estilo cron):
# OnCalendar=*-*-* *:00/10:00   # Cada 10 minutos en punto
Persistent=true                 # Ejecuta tareas pendientes si la RPi estuvo apagada

[Install]
WantedBy=timers.target
```

#### Tipos de Temporizadores
* **Monotónicos (`OnBootSec=`, `OnUnitActiveSec=`)**: Basados en el reloj de tiempo de ejecución del kernel (`CLOCK_MONOTONIC`). No dependen de la hora real ni sufren desfases si el reloj NTP se sincroniza tarde.
* **De tiempo real / Calendario (`OnCalendar=`)**: Basados en el reloj de pared (`CLOCK_REALTIME`). Permiten expresiones exactas (días de la semana, horas fijas).

---

### Estructura de Archivos en la Raspberry Pi:
```text
/home/[USUARIO]/taller-systemd/
├── telemetria.py
└── systemd/
    ├── telemetria.service
    ├── telemetria-timer.service
    └── telemetria.timer
```

---

## Taller parte 1 – Demonio continuo

### Despliegue demonio continuo

1. **Crea la carpeta del proyecto en el directorio del usuario:**
```bash
mkdir -p /home/[USUARIO]/taller-systemd/systemd
cd /home/[USUARIO]/taller-systemd
```

2. **Crear el Script de telemetría:**
```bash
nano telemetria.py
```

3. **Prueba del script:**
```bash
# 1. Probar un envío individual 
python3 telemetria.py once

# 2. Probar el bucle continuo
python3 telemetria.py
```

4. **Crear los archivos de systemd:**
```bash
cd systemd
nano telemetria-timer.service
nano telemetria.service
nano telemetria.timer
cd ..
```

5. **Copiar el archivo al directorio del sistema:**
```bash
sudo cp systemd/telemetria.service /etc/systemd/system/
```

6. **Modificar permisos:**
```bash
sudo chmod 644 /etc/systemd/system/telemetria.service
```

7. **Notificar a Systemd para escanear nuevos archivos:**
```bash
sudo systemctl daemon-reload
```

8. **Habilitar el servicio para que inicie automáticamente en cada arranque:**
```bash
sudo systemctl enable telemetria.service
```

9. **Iniciar el servicio:**
```bash
sudo systemctl start telemetria.service
```

---

### Monitoreo y diagnóstico

1. **Comprueba el estado operativo del demonio:**
```bash
sudo systemctl status telemetria.service
```

2. **Monitoreo de los registros en vivo:**
```bash
journalctl -u telemetria.service -f
```

---

### Prueba de resiliencia

1. **En una terminal, averigua el PID actual del proceso:**
```bash
pgrep -f "telemetria.py"
```

2. **Simula una caída crítica enviando una señal SIGKILL (`kill -9`):**
```bash
sudo kill -9 $(pgrep -f "telemetria.py")
```

3. **Observa en los logs cómo Systemd detecta la muerte súbita y lo revive:**
```bash
journalctl -u telemetria.service -n 15 --no-pager
```

4. **Consulta de nuevo el estado:**
```bash
sudo systemctl status telemetria.service
```

---

## Taller parte 2 – Demonio periódico

### Detener el demonio continuo
Para no duplicar el tráfico de telemetría, detenemos el servicio continuo:
```bash
sudo systemctl stop telemetria.service
sudo systemctl disable telemetria.service
```

---

### Despliegue demonio periódico

1. **Copiar los archivos al directorio del sistema y ajustar permisos:**
```bash
sudo cp systemd/telemetria-timer.service /etc/systemd/system/
sudo cp systemd/telemetria.timer /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/telemetria-timer.service /etc/systemd/system/telemetria.timer
```

2. **Recargar Systemd:**
```bash
sudo systemctl daemon-reload
```

3. **Habilitar e iniciar el timer:**
```bash
sudo systemctl enable telemetria.timer
sudo systemctl start telemetria.timer
```

---

### Monitoreo y diagnóstico

1. **Comprueba el estado operativo del temporizador:**
```bash
systemctl list-timers --all | grep telemetria
```

2. **Monitoreo de los registros en vivo:**
```bash
journalctl -u telemetria-timer.service -f
```
