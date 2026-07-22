# 🔮 Mozárabe Tarot - Bot de Telegram

Bot de Tarot basado en el Tarot de Marsella con tiradas diarias, programación automática y diccionario completo de arcanos.


## 🫖 Contenido 

Interpretaciones personales comparadas con las obras:

- La voie du Tarot. Alejandro Jodorowsky, Marianne Costa. Penguin Random House. 14a. reimpresión. México, mayo 2023.
- The Ultimate Guide to the Tarot Rider Waite. Johannes Fiebig, Evelin Bürger. Arkano Books. 3a. reimpresión, India, septiembre 2022.
- Helping yourself with numerology. Heyln Hitchcock. Editorial Kier, S.A. Argentina, octubre 1993.

## ✨ Funcionalidades

- **Tirada del Día** (1 carta)
- **Tirada de 3 Cartas** (pasado, presente, futuro)
- **Programación diaria automática** (`/programar HH:MM`)
- **Diccionario completo** de los 78 Arcanos Mayores y Arcanos Menores
- Soporte para cartas **invertidas** (imágenes rotadas y su interpretación)
- Interfaz con botones interactivos

## 📁 Estructura del Proyecto

## 🚀 Ejecutar localmente

```bash
# Instalar librería de Python
pip install python-telegram-bot

# Instalar dependencias
pip install -r requirements.txt

# Activar entorno virtual
source venv/bin/activate

# Ejecutar el bot (Telegram previamente instalado y corriendo)
./venv/bin/python bot.py
```

## 📋 **Variables de Entorno Requeridas**

TELEGRAM_TOKEN → Token proporcionado por @BotFather

## 🛠 **Tecnologías**

Python 3.12
python-telegram-bot v21
Pillow (para rotación de cartas)

🧙‍♂️ Administración: @josebenaque en Telegram
