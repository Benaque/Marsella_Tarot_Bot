import json
import random
import logging
import os
import io
import asyncio
import sqlite3
import requests
from deep_translator import GoogleTranslator
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

# --- DICCIONARIO DE COMPATIBILIDAD DE ELEMENTOS ---
SINOSTRIA_ELEMENTOS = {
    "Agua 💧_Agua 💧": "Fusión emocional profunda. Gran empatía y comprensión sin palabras; deben evitar ahogarse en el dramatismo o el exceso de sensibilidad.",
    "Agua 💧_Aire 💨": "Razón vs. emoción. El Aire racionaliza lo que el Agua siente; pueden complementarse si el Aire aprende a validar las emociones y si el Agua respeta el espacio mental del Aire.",
    "Agua 💧_Fuego 🔥": "Vapor y ebullición. El Fuego calienta las emociones del Agua, trayendo pasión; sin embargo, el exceso de Fuego puede evaporar la sensibilidad, o el Agua apagar el entusiasmo.",
    "Agua 💧_Tierra 🌍": "Nutrición mutua. El Agua fertiliza la Tierra para que dé frutos, y la Tierra le da un cauce seguro al Agua. Una relación sumamente protectora y duradera.",
    "Aire 💨_Aire 💨": "Conexión mental estimulante. Excelentes conversaciones, libertad e ideas compartidas. El reto es bajar a la tierra y no quedarse solo en el plano de las ideas o la amistad.",
    "Aire 💨_Fuego 🔥": "El Aire aviva el Fuego. Relación llena de aventuras, pasión y dinamismo. Se inspiran mutuamente para actuar y explorar, logrando una excelente química.",
    "Aire 💨_Tierra 🌍": "Lo práctico y lo intelectual. El Aire aporta visiones amplias y la Tierra se encarga de estructurarlas; deben ser pacientes, pues marchan a ritmos y enfoques muy distintos.",
    "Fuego 🔥_Fuego 🔥": "Pasión explosiva y acción constante. Mucha vitalidad, entusiasmo y franqueza; deben cuidar de no chocar sus egos o entrar en competencias desgastantes.",
    "Fuego 🔥_Tierra 🌍": "Impulso y estructura. El Fuego tiene la iniciativa y la Tierra la materializa. Si logran mediar entre la impulsividad del Fuego y la cautela de la Tierra, serán invencibles.",
    "Tierra 🌍_Tierra 🌍": "Estabilidad, lealtad y compromiso absoluto. Buscan construir a largo plazo con bases muy sólidas. El único reto es evitar que la relación caiga en la rutina o el aburrimiento."
}

# --- MENÚS ---
def obtener_menu_pareja():
    keyboard = [
        [InlineKeyboardButton("♈ Aries", callback_data='pareja_aries'),
         InlineKeyboardButton("♉ Tauro", callback_data='pareja_tauro'),
         InlineKeyboardButton("♊ Géminis", callback_data='pareja_geminis')],
        [InlineKeyboardButton("♋ Cáncer", callback_data='pareja_cancer'),
         InlineKeyboardButton("♌ Leo", callback_data='pareja_leo'),
         InlineKeyboardButton("♍ Virgo", callback_data='pareja_virgo')],
        [InlineKeyboardButton("♎ Libra", callback_data='pareja_libra'),
         InlineKeyboardButton("♏ Escorpio", callback_data='pareja_escorpio'),
         InlineKeyboardButton("♐ Sagitario", callback_data='pareja_sagitario')],
        [InlineKeyboardButton("♑ Capricornio", callback_data='pareja_capricornio'),
         InlineKeyboardButton("♒ Acuario", callback_data='pareja_acuario'),
         InlineKeyboardButton("♓ Piscis", callback_data='pareja_piscis')]
    ]
    return InlineKeyboardMarkup(keyboard)

def obtener_menu_principal():
    keyboard = [
        [InlineKeyboardButton("⏰ Programar carta diaria", callback_data='menu_programar')],
        [InlineKeyboardButton("⚙️ Configurar mi signo", callback_data='menu_signo')]
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
        [InlineKeyboardButton("🔙 Volver al inicio", callback_data='volver_inicio')]
    ]
    return InlineKeyboardMarkup(keyboard)

def obtener_teclado_persistente():
    keyboard = [
        [KeyboardButton("🃏 Tirada del día"), KeyboardButton("🎲 Tirada de tres cartas")],
        [KeyboardButton("❤️ Tirada de compatibilidad del día")],
        [KeyboardButton("⚙️ Ajustes de signo y programación")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# --- FUNCIÓN DE HORÓSCOPO (API Astrology.com / Ohmanda) ---
def obtener_horoscopo_diario(signo_espanol):
    traduccion_signos = {
        "aries": "aries", "tauro": "taurus", "geminis": "gemini",
        "cancer": "cancer", "leo": "leo", "virgo": "virgo",
        "libra": "libra", "escorpio": "scorpio", "sagitario": "sagittarius",
        "capricornio": "capricorn", "acuario": "aquarius", "piscis": "pisces"
    }
    
    signo_en = traduccion_signos.get(signo_espanol.lower(), "aries")
    url = f"https://ohmanda.com/api/horoscope/{signo_en}/"
    
    try:
        respuesta = requests.get(url, timeout=7)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            horoscopo_ingles = datos.get("horoscope", "")
            if horoscopo_ingles:
                horoscopo_espanol = GoogleTranslator(source='en', target='es').translate(horoscopo_ingles)
                return f"🔮 <b>Horóscopo del Día:</b>\n{horoscopo_espanol}"
    except Exception as e:
        logging.error(f"⚠️ Error obteniendo horóscopo: {e}")
    
    return None

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
        titulo = f"🃏 <b>{nombre}</b> (invertida 🙃)"
        interpretacion = carta["significado_invertido"]
    else:
        titulo = f"🃏 <b>{nombre}</b> (al derecho ⭐)"
        interpretacion = carta["significado_derecho"]
        
    texto_final = f"{titulo}\n\n<b>Interpretación:</b>\n{interpretacion}"
    
    # Horóscopo diario directo (sin texto de sinergia de elementos)
    if signo_usuario and signo_usuario in DATOS_ASTROLOGICOS:
        horoscopo_api = obtener_horoscopo_diario(signo_usuario.lower())
        if horoscopo_api:
            texto_final += f"\n\n{horoscopo_api}"
        
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
                titulo_carta = f"{nombre_real} (invertida 🙃)"
            else:
                significado = datos_carta['significado_derecho']
                titulo_carta = f"{nombre_real} (al derecho ⭐)"
            
            # Texto exclusivo de la carta y su posición temporal
            texto_lectura = f"📌 <b>{posicion}: {titulo_carta}</b>\n\n📖 <i>{significado}</i>"
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
        f"¡Hola, {usuario}! 🔮 Bienvenido a los ajustes de <b>Mozárabe Tarot</b>.\n\n"
        "Aquí puedes programar tu lectura diaria (ej: <code>/programar 08:30</code>) "
        "o configurar tu signo zodiacal para recibir tu predicción personalizada."
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
    
    if texto == "🃏 Tirada del día":
        await ejecutar_tirada_dia(chat_id, context)
        
    elif texto == "🎲 Tirada de tres cartas":
        mensaje_espera = await update.message.reply_text("🔮 Mezclando el mazo y sacando tus 3 cartas...")
        await ejecutar_tres_cartas(chat_id, context, mensaje_espera)
        
    elif texto == "❤️ Tirada de compatibilidad del día":
        perfil = obtener_perfil(chat_id)
        if not perfil.get("signo"):
            await update.message.reply_text(
                "⚠️ Para leer tu compatibilidad, primero necesito conocer tu propia energía. Configura tu signo aquí:",
                reply_markup=obtener_menu_signos()
            )
        else:
            await update.message.reply_text(
                "💞 <b>Tirada de compatibilidad</b>\n\n¿Cuál es el signo de la persona especial?",
                parse_mode="HTML",
                reply_markup=obtener_menu_pareja()
            )
            
    elif texto == "⚙️ Ajustes de signo y programación":
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
        await update.effective_message.reply_text(
            "❌ Error interno: JobQueue no está activo.",
            reply_markup=obtener_teclado_persistente()
        )
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
            parse_mode="HTML",
            reply_markup=obtener_teclado_persistente()
        )
        
    except (IndexError, ValueError):
        await update.effective_message.reply_text(
            "❌ Formato incorrecto. Por favor usa:\n<code>/programar HH:MM</code> (ej: <code>/programar 07:15</code>)",
            parse_mode="HTML",
            reply_markup=obtener_teclado_persistente()
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
        mensaje_signo = "✨ <b>Configura tu Signo Zodiacal</b> ✨\n\nElige tu signo para recibir tu horóscopo diario y consultar compatibilidades:"
        try:
            await query.message.delete()
        except BadRequest:
            pass
        await context.bot.send_message(chat_id=chat_id, text=mensaje_signo, parse_mode="HTML", reply_markup=obtener_menu_signos())

    elif query.data.startswith('set_signo_'):
        signo_elegido = query.data.split('_')[2] 
        astro = DATOS_ASTROLOGICOS[signo_elegido]
        
        guardar_perfil(chat_id, signo=signo_elegido)
        mensaje_exito = f"🌟 ¡Excelente! He guardado tu signo como <b>{astro['nombre']}</b>."
        
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
    
    elif query.data.startswith('pareja_'):
        signo_pareja = query.data.split('_')[1].lower()
        perfil = obtener_perfil(chat_id)
        signo_usuario = perfil.get("signo")
        
        if not signo_usuario or signo_usuario not in DATOS_ASTROLOGICOS:
            await query.answer("⚠️ Faltan datos astrológicos", show_alert=True)
            await query.edit_message_text(
                "🔮 <b>Los astros están incompletos.</b>\n\n"
                "Para calcular la compatibilidad, primero necesito conocer tu propio signo zodiacal.\n"
                "Por favor, ve a <b>⚙️ Ajustes de signo</b> y regístralo ahí.",
                parse_mode="HTML"
            )
            return

        astro_user = DATOS_ASTROLOGICOS[signo_usuario]
        astro_pareja = DATOS_ASTROLOGICOS[signo_pareja]

        elementos = sorted([astro_user['elemento'], astro_pareja['elemento']])
        llave_sinergia = f"{elementos[0]}_{elementos[1]}"
        texto_sinergia = SINOSTRIA_ELEMENTOS.get(llave_sinergia, "Sinergia en proceso...")
        
        claves_cartas = list(tarot_db.keys())
        carta_id = random.choice(claves_cartas)
        carta = tarot_db[carta_id]
        esta_invertida = random.choice([True, False])
        
        nombre = carta["nombre"]
        titulo = f"🃏 <b>{nombre}</b> (invertida 🙃)" if esta_invertida else f"🃏 <b>{nombre}</b> (al derecho ⭐)"
        interpretacion = carta["significado_invertido"] if esta_invertida else carta["significado_derecho"]
        
        mensaje_final = (
            f"💞 <b>VÍNCULO DEL DÍA ({astro_user['nombre']} & {astro_pareja['nombre']})</b> 💞\n\n"
            f"{titulo}\n\n"
            f"<b>Interpretación:</b>\n{interpretacion}\n\n"
            f"✨ <b>Sinergia de Elementos ({astro_user['elemento']} + {astro_pareja['elemento']}):</b>\n"
            f"{texto_sinergia}"
        )
        
        ruta_imagen = f"imagenes/{carta_id}.jpg"
        
        try:
            await query.message.delete()
        except BadRequest:
            pass
            
        mensaje_espera = await context.bot.send_message(chat_id=chat_id, text="🔮 Cruzando energías y sacando la carta del vínculo...")
        await asyncio.sleep(2)
        
        try:
            if len(mensaje_final) > 1000:
                caption_corta = f"💞 <b>VÍNCULO DEL DÍA ({astro_user['nombre']} & {astro_pareja['nombre']})</b>"
                if esta_invertida:
                    memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                    await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=caption_corta, parse_mode="HTML")
                else:
                    with open(ruta_imagen, 'rb') as foto:
                        await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=caption_corta, parse_mode="HTML")
                await context.bot.send_message(chat_id=chat_id, text=mensaje_final, parse_mode="HTML")
            else:
                if esta_invertida:
                    memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                    await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=mensaje_final, parse_mode="HTML")
                else:
                    with open(ruta_imagen, 'rb') as foto:
                        await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=mensaje_final, parse_mode="HTML")
        except Exception as e:
            logging.error(f"⚠️ Error enviando carta de compatibilidad: {e}")
            await context.bot.send_message(chat_id=chat_id, text=mensaje_final, parse_mode="HTML")
        
        try:
            await mensaje_espera.delete()
        except BadRequest:
            pass

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