# 🔮 Mozárabe Tarot - Bot de Telegram

Bot de tarot aleatorio basado en el **Tarot de Marsella**.


## 🫖 Contenido 

Interpretaciones personales comparadas con las obras:

- La voie du Tarot. Alejandro Jodorowsky, Marianne Costa. Penguin Random House. 14a reimpresión. Ciudad de México, mayo 2023.
- The Ultimate Guide to the Tarot Rider Waite. Johannes Fiebig, Evelin Bürger. Arkano Books. 3a reimpresión, Nueva Delhi, septiembre 2022.
- Helping yourself with numerology. Heyln Hitchcock. Editorial Kier, S.A. 4a edición. Buenos Aires, octubre 1993.
- El Tarot de Marsella. Julian M. White. Editorial Sirio. S/I impresión. Málaga, agosto 2024.

## ✨ Funcionalidades

- **Tirada del día** Una carta
- **Tirada de tres cartas** Simbolizan una vista rápida del mpasado, presente y futuro
- **Programación diaria automática** Mediante comando `/programar HH:MM`
- **Breve interpretación** de los 78 Arcanos: Mayores y Menores
- Soporte para cartas **invertidas** Imágenes rotadas y su significado
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

- Python 3.12
- python-telegram-bot v21
- Pillow (para rotación de cartas)

🧙‍♂️ Administración: @josebenaque en Telegram
