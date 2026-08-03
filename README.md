# 🔮 Mozárabe Tarot - Bot de Telegram

Bot de tarot aleatorio basado en el **Tarot de Marsella**.


## 🫖 Contenido 

Interpretaciones personales y textos extraídos de las obras:

- *La voie du Tarot*. Alejandro Jodorowsky, Marianne Costa. Penguin Random House. 14a reimpresión. Ciudad de México, mayo 2023.
- *The Ultimate Guide to the Tarot Rider Waite*. Johannes Fiebig, Evelin Bürger. Arkano Books. 3a reimpresión, Nueva Delhi, septiembre 2022.
- *Helping yourself with numerology*. Heyln Hitchcock. Editorial Kier, S.A. 4a edición. Buenos Aires, octubre 1993.
- *The Tarot: A Key to the Wisdom of the Ages*. Paul Foster Case. Builders of Adytum, Ltd. New York, julio 2006.

## ✨ Funcionalidades

- **Tirada del día**: una carta aleatoria que simboliza el consejo del día
- **Tirada de tres cartas**: tres cartas aleatorias que simbolizan una lectura rápida del pasado, presente y futuro
- **Programación diaria automática** Mediante comando: `/programar HH:MM`
- Soporte para cartas **invertidas** Imágenes rotadas y su significado
- Interfaz con botones interactivos, diseñado para interfaz móvil y de escritorio en Telegram

## 📁 Estructura del Proyecto

## 🚀 Tecnología para ejecución local

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

## 🛠 **Tecnologías para ejecución pública**

- python-telegram-bot[webhooks,job-queue]>=20.0
- Pillow>=9.0.0
- requests>=2.31.0
- deep-translator>=1.11.4
- beautifulsoup4>=4.12.0
- WEBHOOK_URL y SQLlite recomendado

🧙‍♂️ E-mail: jfk4dk10r@mozmail.com 📬

👾 Este bot fue diseñado únicamente para fines de entretenimiento y no busca sustituir a ningún ser humano. La interpretación que se ha colocado es meramente personal y subjetiva, con citas de diversos autores a las que se pueden relacionar a cada carta. Para lecturas personalizadas, se recomienda acudir con tarotistas profesionales.

Proyecto OpenSource: https://creativecommons.org/licenses/by/4.0/ 
