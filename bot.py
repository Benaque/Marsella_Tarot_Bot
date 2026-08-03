import json
import random
import logging
import os
import io
import asyncio
import sqlite3
from zoneinfo import ZoneInfo
from datetime import time
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest
from PIL import Image

# Configuración de registros
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Cargar la base de datos de Tarot
with open('tarot_db.json', 'r', encoding='utf-8') as f:
    tarot_db = json.load(f)

# Base de Datos Astrológica
DATOS_ASTROLOGICOS = {
    "aries": {"nombre": "♈ Aries", "elemento": "Fuego 🔥", "enfoque": "la acción, el impulso y la iniciativa"},
    "tauro": {"nombre": "♉ Tauro", "elemento": "Tierra 🌍", "enfoque": "la estabilidad, el confort y la paciencia"},
    "geminis": {"nombre": "♊ Géminis", "elemento": "Aire 💨", "enfoque": "la comunicación, la adaptabilidad y la mente"},
    "cancer": {"nombre": "♋ Cáncer", "elemento": "Agua 💧", "enfoque": "la emoción, el cuidado y la intuición"},
    "leo": {"nombre": "♌ Leo", "elemento": "Fuego 🔥", "enfoque": "la autoexpresión, la confianza y el brillo"},
    "virgo": {"nombre": "♍ Virgo", "elemento": "Tierra 🌍", "enfoque": "el análisis, el detalle y el orden"},
    "libra": {"nombre": "♎ Libra", "elemento": "Aire 💨", "enfoque": "el equilibrio, la armonía y las relaciones"},
    "escorpio": {"nombre": "♏ Escorpio", "elemento": "Agua 💧", "enfoque": "la transformación, la intensidad y la profundidad"},
    "sagitario": {"nombre": "♐ Sagitario", "elemento": "Fuego 🔥", "enfoque": "la expansión, la aventura y la verdad"},
    "capricornio": {"nombre": "♑ Capricornio", "elemento": "Tierra 🌍", "enfoque": "la estructura, la ambición y la perseverancia"},
    "acuario": {"nombre": "♒ Acuario", "elemento": "Aire 💨", "enfoque": "la innovación, la rebeldía y la libertad"},
    "piscis": {"nombre": "♓ Piscis", "elemento": "Agua 💧", "enfoque": "la empatía, la fantasía y la espiritualidad"}
}

# --- MENÚS ---
def obtener_menu_principal():
    keyboard = [
        [InlineKeyboardButton("⏰ Programar Carta Diaria", callback_data='menu_programar')],
        [InlineKeyboardButton("⚙️ Configurar mi Signo", callback_data='menu_signo')]
    ]
    return InlineKeyboardMarkup(keyboard)

def obtener_menu_signos():
    keyboard = [
        [InlineKeyboardButton("♈ Aries", callback_data='set_signo_aries'),
         InlineKeyboardButton("♉ Tauro", callback_data='set_signo_tauro'),
         InlineKeyboardButton("♊ Géminis", callback_data='set_signo_geminis')],
        [InlineKeyboardButton("♋ Cáncer", callback_data='set_signo_cancer'),
         InlineKeyboardButton("♌ Leo", callback_data='set_signo_leo'),
         InlineKeyboardButton("♍ Virgo", callback_data='set_signo_virgo')],
        [InlineKeyboardButton("♎ Libra", callback_data='set_signo_libra'),
         InlineKeyboardButton("♏ Escorpio", callback_data='set_signo_escorpio'),
         InlineKeyboardButton("♐ Sagitario", callback_data='set_signo_sagitario')],
        [InlineKeyboardButton("♑ Capricornio", callback_data='set_signo_capricornio'),
         InlineKeyboardButton("♒ Acuario", callback_data='set_signo_acuario'),
         InlineKeyboardButton("♓ Piscis", callback_data='set_signo_piscis')],
        [InlineKeyboardButton("🔙 Volver al Inicio", callback_data='volver_inicio')]
    ]
    return InlineKeyboardMarkup(keyboard)

def obtener_teclado_persistente():
    keyboard = [
        [KeyboardButton("🃏 Tirada del Día"), KeyboardButton("🎲 3 Cartas")],
        [KeyboardButton("⚙️ Menú de Ajustes")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# --- BASE DE DATOS SQLITE ---
os.makedirs('/app/data', exist_ok=True) if os.path.exists('/app') else os.makedirs('data', exist_ok=True)
DB_NAME = '/app/data/perfiles.db' if os.path.exists('/app') else 'data/perfiles.db'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS perfiles (
                chat_id TEXT PRIMARY KEY,
                hora INTEGER,
                minuto INTEGER,
                signo TEXT
            )
        ''')
        conn.commit()

def obtener_perfil(chat_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT hora, minuto, signo FROM perfiles WHERE chat_id = ?', (str(chat_id),))
        fila = cursor.fetchone()
    if fila:
        return {"hora": fila[0], "minuto": fila[1], "signo": fila[2]}
    return {}

def obtener_todos_perfiles():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT chat_id, hora, minuto, signo FROM perfiles')
        filas = cursor.fetchall()
    perfiles = {}
    for fila in filas:
        chat_id, hora, minuto, signo = fila
        perfiles[chat_id] = {"hora": hora, "minuto": minuto, "signo": signo}
    return perfiles

def guardar_perfil(chat_id, hora=None, minuto=None, signo=None):
    perfil_actual = obtener_perfil(chat_id)
    nueva_hora = hora if hora is not None else perfil_actual.get("hora")
    nuevo_minuto = minuto if minuto is not None else perfil_actual.get("minuto")
    nuevo_signo = signo if signo is not None else perfil_actual.get("signo")
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO perfiles (chat_id, hora, minuto, signo)
            VALUES (?, ?, ?, ?)
        ''', (str(chat_id), nueva_hora, nuevo_minuto, nuevo_signo))
        conn.commit()

# --- LÓGICA DE CARTAS E IMÁGENES ---
def procesar_imagen_invertida(ruta_imagen):
    with Image.open(ruta_imagen) as imagen_original:
        imagen_girada = imagen_original.rotate(180)
        memoria = io.BytesIO()
        memoria.name = 'girada.jpg'
        imagen_girada.save(memoria, 'JPEG')
        memoria.seek(0)
        return memoria 

def generar_datos_carta_aleatoria(signo_usuario=None):
    claves_cartas = list(tarot_db.keys())
    carta_id = random.choice(claves_cartas)
    carta = tarot_db[carta_id]
    esta_invertida = random.choice([True, False])

    nombre = carta["nombre"]
    if esta_invertida:
        titulo = f"🃏 <b>{nombre}</b> (Invertida 🙃)"
        interpretacion = carta["significado_invertido"]
    else:
        titulo = f"🃏 <b>{nombre}</b> (Al Derecho ⭐)"
        interpretacion = carta["significado_derecho"]
        
    texto_final = f"{titulo}\n\n<b>Interpretación:</b>\n{interpretacion}"
    
    if signo_usuario and signo_usuario in DATOS_ASTROLOGICOS:
        astro = DATOS_ASTROLOGICOS[signo_usuario]
        texto_final += f"\n\n✨ <b>Sinergia Astrológica ({astro['nombre']}):</b>\nComo tu energía es de {astro['elemento']}, al integrar el mensaje de esta carta enfócate en {astro['enfoque']}."
        
    ruta_imagen = f"imagenes/{carta_id}.jpg"
    return texto_final, ruta_imagen, carta_id, esta_invertida

async def ejecutar_tirada_dia(chat_id, context):
    perfil = obtener_perfil(chat_id)
    signo_usuario = perfil.get("signo")
    
    texto_final, ruta_imagen, carta_id, esta_invertida = generar_datos_carta_aleatoria(signo_usuario)
    texto_dia = f"🌟 <b>TU CARTA DEL DÍA</b> 🌟\n\n{texto_final}"
    
    try:
        if len(texto_dia) > 1000:
            caption_corta = "🌟 <b>TU CARTA DEL DÍA</b> 🌟"
            if esta_invertida:
                memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=caption_corta, parse_mode="HTML")
            else:
                with open(ruta_imagen, 'rb') as foto:
                    await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=caption_corta, parse_mode="HTML")
            await context.bot.send_message(chat_id=chat_id, text=texto_dia, parse_mode="HTML")
        else:
            if esta_invertida:
                memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_dia, parse_mode="HTML")
            else:
                with open(ruta_imagen, 'rb') as foto:
                    await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_dia, parse_mode="HTML")
    except FileNotFoundError:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_dia}", parse_mode="HTML")

async def ejecutar_tres_cartas(chat_id, context, mensaje_espera):
    perfil = obtener_perfil(chat_id)
    signo_usuario = perfil.get("signo")
    
    try:
        claves_cartas = list(tarot_db.keys())
        cartas_seleccionadas = random.sample(claves_cartas, 3)
        posiciones = ["Pasado 🕰️", "Presente 👁️", "Futuro ✨"]
        
        for i in range(3):
            clave = cartas_seleccionadas[i]
            datos_carta = tarot_db[clave]
            posicion = posiciones[i]
            nombre_real = datos_carta['nombre']
            esta_invertida = random.choice([True, False])
            
            if esta_invertida:
                significado = datos_carta['significado_invertido']
                titulo_carta = f"{nombre_real} (Invertida 🙃)"
            else:
                significado = datos_carta['significado_derecho']
                titulo_carta = f"{nombre_real} (Al derecho ⭐)"
            
            texto_lectura = f"📌 <b>{posicion}: {titulo_carta}</b>\n\n📖 <i>{significado}</i>"
            
            if signo_usuario and signo_usuario in DATOS_ASTROLOGICOS:
                astro = DATOS_ASTROLOGICOS[signo_usuario]
                texto_lectura += f"\n\n✨ <i>Sinergia ({astro['nombre']}): Tu energía de {astro['elemento']} influye en esta posición.</i>"
            
            ruta_imagen = f"imagenes/{clave}.jpg" 
            
            try:
                if len(texto_lectura) > 1000:
                    caption_corta = f"📌 <b>{posicion}: {titulo_carta}</b>"
                    if esta_invertida:
                        memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                        await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=caption_corta, parse_mode="HTML")
                    else:
                        with open(ruta_imagen, 'rb') as foto:
                            await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=caption_corta, parse_mode="HTML")
                    
                    await context.bot.send_message(chat_id=chat_id, text=texto_lectura, parse_mode="HTML")
                else:
                    if esta_invertida:
                        memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                        await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_lectura, parse_mode="HTML")
                    else:
                        with open(ruta_imagen, 'rb') as foto:
                            await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_lectura, parse_mode="HTML")
            except Exception as e:
                logging.error(f"⚠️ Error enviando imagen {ruta_imagen}: {e}")
                try:
                    await context.bot.send_message(chat_id=chat_id, text=texto_lectura, parse_mode="HTML")
                except Exception as inner_e:
                    logging.error(f"⚠️ Error fatal enviando carta {i+1}: {inner_e}")
            
            await asyncio.sleep(2.5)
            
    finally:
        if mensaje_espera:
            try:
                await mensaje_espera.delete()
            except BadRequest:
                pass

async def enviar_menu_ajustes(chat_id, context, usuario):
    mensaje = (
        f"¡Hola, {usuario}! 🔮 Bienvenido a los Ajustes de <b>Mozárabe Tarot</b>.\n\n"
        "Desde aquí puedes programar tu lectura diaria (Ej: <code>/programar 08:30</code>) "
        "o configurar tu signo zodiacal para recibir sinergias personalizadas."
    )
    ruta_bienvenida = "imagenes/5L5ZT.jpg"
    
    try:
        with open(ruta_bienvenida, 'rb') as foto:
            await context.bot.send_photo(
                chat_id=chat_id, 
                photo=foto, 
                caption=mensaje, 
                reply_markup=obtener_menu_principal(), 
                parse_mode="HTML"
            )
    except FileNotFoundError:
        await context.bot.send_message(
            chat_id=chat_id, 
            text=mensaje, 
            reply_markup=obtener_menu_principal(), 
            parse_mode="HTML"
        )

# --- HANDLERS PRINCIPALES ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🃏 Preparando tu mesa de Tarot...", 
        reply_markup=obtener_teclado_persistente()
    )
    chat_id = update.effective_chat.id
    usuario = update.effective_user.first_name
    await enviar_menu_ajustes(chat_id, context, usuario)

async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    chat_id = update.effective_chat.id
    
    if texto == "🃏 Tirada del Día":
        await ejecutar_tirada_dia(chat_id, context)
        
    elif texto == "🎲 3 Cartas":
        mensaje_espera = await update.message.reply_text("🔮 Mezclando el mazo y sacando tus 3 cartas...")
        await ejecutar_tres_cartas(chat_id, context, mensaje_espera)
        
    elif texto == "⚙️ Menú de Ajustes":
        usuario = update.effective_user.first_name
        await enviar_menu_ajustes(chat_id, context, usuario)

async def enviar_carta_automatica(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    
    perfil = obtener_perfil(chat_id)
    signo_usuario = perfil.get("signo")
    
    texto_final, ruta_imagen, carta_id, esta_invertida = generar_datos_carta_aleatoria(signo_usuario)
    texto_automatico = f"🧞‍♀️ <b>¡Tu carta del día automática ha llegado!</b> 🧞‍♂️\n\n{texto_final}"
    
    try:
        if len(texto_automatico) > 1000:
            caption_corta = "🧞‍♀️ <b>¡Tu carta del día automática ha llegado!</b> 🧞‍♂️"
            if esta_invertida:
                memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=caption_corta, parse_mode="HTML")
            else:
                with open(ruta_imagen, 'rb') as foto:
                    await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=caption_corta, parse_mode="HTML")
            await context.bot.send_message(chat_id=chat_id, text=texto_automatico, parse_mode="HTML")
        else:
            if esta_invertida:
                memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_automatico, parse_mode="HTML")
            else:
                with open(ruta_imagen, 'rb') as foto:
                    await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_automatico, parse_mode="HTML")
    except FileNotFoundError:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_automatico}", parse_mode="HTML")

async def programar_hora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    usuario = update.effective_user.first_name
    
    if context.job_queue is None:
        await update.effective_message.reply_text("❌ Error interno: JobQueue no está activo.")
        return

    try:
        hora_texto = context.args[0]
        hora_str, minuto_str = hora_texto.split(":")
        hora = int(hora_str)
        minuto = int(minuto_str)
        
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            raise ValueError
        
        nombre_tarea = str(chat_id)
        tareas_actuales = context.job_queue.get_jobs_by_name(nombre_tarea)
        for tarea in tareas_actuales:
            tarea.schedule_removal()
            
        zona_horaria = ZoneInfo("America/Mexico_City") 
        hora_programada = time(hour=hora, minute=minuto, tzinfo=zona_horaria)
        
        guardar_perfil(chat_id, hora=hora, minuto=minuto)
        
        context.job_queue.run_daily(
            enviar_carta_automatica,
            time=hora_programada,
            chat_id=chat_id,
            name=nombre_tarea
        )
        
        await update.effective_message.reply_text(
            f"✅ ¡Perfecto, {usuario}! He programado tu lectura diaria para las <b>{hora_texto}</b> todos los días.",
            parse_mode="HTML"
        )
        
    except (IndexError, ValueError):
        await update.effective_message.reply_text(
            "❌ Formato incorrecto. Por favor usa:\n<code>/programar HH:MM</code> (ej: <code>/programar 07:15</code>)",
            parse_mode="HTML"
        )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    chat_id = update.effective_chat.id

    if query.data == 'menu_programar':
        mensaje_instrucciones = (
            "⏰ <b>Configuración de tu alarma diaria</b>\n\n"
            "Para recibir tu carta automáticamente, escribe en el chat el comando <code>/programar</code> seguido de la hora.\n\n"
            "👉 <b>Ejemplo:</b> <code>/programar 08:30</code>"
        )
        try:
            await query.message.delete()
        except BadRequest:
            pass
        await context.bot.send_message(chat_id=chat_id, text=mensaje_instrucciones, parse_mode="HTML", reply_markup=obtener_menu_principal())

    elif query.data == 'menu_signo':
        mensaje_signo = "✨ <b>Sinergia Astrológica</b> ✨\n\nElige tu signo zodiacal para que el Tarot Mozárabe cruce la energía de tu elemento con el mensaje de tus cartas:"
        try:
            await query.message.delete()
        except BadRequest:
            pass
        await context.bot.send_message(chat_id=chat_id, text=mensaje_signo, parse_mode="HTML", reply_markup=obtener_menu_signos())

    elif query.data.startswith('set_signo_'):
        signo_elegido = query.data.split('_')[2] 
        astro = DATOS_ASTROLOGICOS[signo_elegido]
        
        guardar_perfil(chat_id, signo=signo_elegido)
        
        mensaje_exito = f"🌟 ¡Excelente! He guardado tu signo como <b>{astro['nombre']}</b>.\n\nA partir de ahora, tus tiradas incluirán una sinergia basada en tu energía de {astro['elemento']}."
        
        try:
            await query.message.edit_text(text=mensaje_exito, parse_mode="HTML", reply_markup=obtener_menu_principal())
        except BadRequest:
            pass

    elif query.data == 'volver_inicio':
        try:
            await query.message.delete()
        except BadRequest:
            pass
        usuario = update.effective_user.first_name
        await enviar_menu_ajustes(chat_id, context, usuario)

def restaurar_alarmas(app: Application):
    perfiles = obtener_todos_perfiles()
    zona_horaria = ZoneInfo("America/Mexico_City")
    
    restauradas = 0
    for chat_id_str, datos in perfiles.items():
        if datos.get("hora") is not None and datos.get("minuto") is not None:
            chat_id = int(chat_id_str)
            hora = datos["hora"]
            minuto = datos["minuto"]
            
            hora_programada = time(hour=hora, minute=minuto, tzinfo=zona_horaria)
            nombre_tarea = str(chat_id)
            
            app.job_queue.run_daily(
                enviar_carta_automatica,
                time=hora_programada,
                chat_id=chat_id,
                name=nombre_tarea
            )
            restauradas += 1
        
    if restauradas > 0:
        logging.info(f"🔮 Se han restaurado {restauradas} alarmas programadas desde SQLite.")

def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    if not TOKEN:
        raise ValueError("❌ ERROR: La variable de entorno TELEGRAM_TOKEN está vacía o no existe en Railway.")
        
    init_db()
        
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("programar", programar_hora))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))
    
    restaurar_alarmas(app)
    
    PORT = int(os.environ.get('PORT', '8443'))
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
    
    if WEBHOOK_URL:
        logging.info(f"🔮 Iniciando en modo WEBHOOK en el puerto {PORT}...")
        url_limpia = WEBHOOK_URL.rstrip('/')
        
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{url_limpia}/{TOKEN}",
            drop_pending_updates=True
        )
    else:
        logging.info("🔮 WEBHOOK_URL no definida. Iniciando en modo POLLING...")
        app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()