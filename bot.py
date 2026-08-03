import json
import random
import logging
import os
import io
import asyncio
from zoneinfo import ZoneInfo
from datetime import time
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
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

def obtener_menu_principal():
    keyboard = [
        [InlineKeyboardButton("🃏 Tirada del Día", callback_data='tirada_dia'),
         InlineKeyboardButton("🎲 3 Cartas", callback_data='menu_tres_cartas')],
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

# Cargar perfiles de usuarios
ARCHIVO_PERFILES = 'alarmas_db.json'

def cargar_perfiles():
    if os.path.exists(ARCHIVO_PERFILES):
        if os.path.getsize(ARCHIVO_PERFILES) > 0:
            with open(ARCHIVO_PERFILES, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print("⚠️ Advertencia: El archivo de perfiles estaba corrupto o vacío.")
                    return {}
    return {}

def guardar_perfiles(perfiles):
    with open(ARCHIVO_PERFILES, 'w', encoding='utf-8') as f:
        json.dump(perfiles, f, indent=4)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje = (
        f"¡Hola, {usuario}! 🔮 Bienvenido a <b>Mozárabe Tarot</b>.\n\n"
        "Puedes pedir cartas, programar tu lectura diaria (Ej: <code>/programar 08:30</code>) "
        "o configurar tu signo zodiacal para recibir sinergias personalizadas.\n\n"
        "¿Qué deseas consultar hoy?"
    )
    await update.message.reply_text(
        text=mensaje, 
        reply_markup=obtener_menu_principal(), 
        parse_mode="HTML"
    )

async def enviar_carta_automatica(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    
    perfiles = cargar_perfiles()
    signo_usuario = perfiles.get(str(chat_id), {}).get("signo")
    
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
        
        perfiles = cargar_perfiles()
        if str(chat_id) not in perfiles:
            perfiles[str(chat_id)] = {}
        perfiles[str(chat_id)]["hora"] = hora
        perfiles[str(chat_id)]["minuto"] = minuto
        guardar_perfiles(perfiles)
        
        await update.effective_message.reply_text(
            f"✅ ¡Perfecto, {usuario}! He programado tu lectura diaria para las <b>{hora_texto}</b> todos los días.",
            reply_markup=obtener_menu_principal(),
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
        
        perfiles = cargar_perfiles()
        if str(chat_id) not in perfiles:
            perfiles[str(chat_id)] = {}
        perfiles[str(chat_id)]["signo"] = signo_elegido
        guardar_perfiles(perfiles)
        
        mensaje_exito = f"🌟 ¡Excelente! He guardado tu signo como <b>{astro['nombre']}</b>.\n\nA partir de ahora, tus tiradas incluirán una sinergia basada en tu energía de {astro['elemento']}."
        
        try:
            await query.message.edit_text(text=mensaje_exito, parse_mode="HTML", reply_markup=obtener_menu_principal())
        except BadRequest:
            pass

    elif query.data == "menu_tres_cartas":
        perfiles = cargar_perfiles()
        signo_usuario = perfiles.get(str(chat_id), {}).get("signo")
        
        if query.message.photo:
            try:
                await query.message.delete()
            except BadRequest:
                pass
            mensaje_espera = await context.bot.send_message(chat_id=chat_id, text="🔮 Mezclando el mazo y sacando tus 3 cartas...")
        else:
            mensaje_espera = await query.edit_message_text(text="🔮 Mezclando el mazo y sacando tus 3 cartas...")
        
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
                teclado = obtener_menu_principal() if i == 2 else None
                
                try:
                    if len(texto_lectura) > 1000:
                        caption_corta = f"📌 <b>{posicion}: {titulo_carta}</b>"
                        if esta_invertida:
                            memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                            await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=caption_corta, parse_mode="HTML")
                        else:
                            with open(ruta_imagen, 'rb') as foto:
                                await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=caption_corta, parse_mode="HTML")
                        
                        await context.bot.send_message(chat_id=chat_id, text=texto_lectura, parse_mode="HTML", reply_markup=teclado)
                    else:
                        if esta_invertida:
                            memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                            await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_lectura, parse_mode="HTML", reply_markup=teclado)
                        else:
                            with open(ruta_imagen, 'rb') as foto:
                                await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_lectura, parse_mode="HTML", reply_markup=teclado)
                except Exception as e:
                    print(f"⚠️ Error enviando imagen {ruta_imagen}: {e}")
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=texto_lectura, parse_mode="HTML", reply_markup=teclado)
                    except Exception as inner_e:
                        print(f"⚠️ Error fatal enviando carta {i+1}: {inner_e}")
                
                await asyncio.sleep(2.5)
                
        finally:
            try:
                await mensaje_espera.delete()
            except BadRequest:
                pass

    elif query.data == 'volver_inicio':
        usuario = update.effective_user.first_name
        mensaje = (
            f"¡Hola, {usuario}! 🔮 Bienvenido a <b>Mozárabe Tarot</b>.\n\n"
            "Puedes pedir cartas, programar tu lectura diaria (Ej: <code>/programar 08:30</code>) "
            "o configurar tu signo zodiacal para recibir sinergias personalizadas.\n\n"
            "¿Qué deseas consultar hoy?"
        )
        if query.message.photo:
            try:
                await query.message.delete()
            except BadRequest:
                pass
            await context.bot.send_message(chat_id=chat_id, text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="HTML")
        else:
            await query.message.edit_text(text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="HTML")

    elif query.data == 'tirada_dia':
        perfiles = cargar_perfiles()
        signo_usuario = perfiles.get(str(chat_id), {}).get("signo")
        
        try:
            await query.message.delete()
        except BadRequest:
            pass
            
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
                await context.bot.send_message(chat_id=chat_id, text=texto_dia, parse_mode="HTML", reply_markup=obtener_menu_principal())
            else:
                if esta_invertida:
                    memoria = await asyncio.to_thread(procesar_imagen_invertida, ruta_imagen)
                    await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_dia, parse_mode="HTML", reply_markup=obtener_menu_principal())
                else:
                    with open(ruta_imagen, 'rb') as foto:
                        await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_dia, parse_mode="HTML", reply_markup=obtener_menu_principal())
        except FileNotFoundError:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_dia}", parse_mode="HTML", reply_markup=obtener_menu_principal())

def restaurar_alarmas(app: Application):
    perfiles = cargar_perfiles()
    zona_horaria = ZoneInfo("America/Mexico_City")
    
    restauradas = 0
    for chat_id_str, datos in perfiles.items():
        if "hora" in datos and "minuto" in datos:
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
        print(f"🔮 Se han restaurado {restauradas} alarmas programadas en memoria.")

def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    if not TOKEN:
        raise ValueError("❌ ERROR: La variable de entorno TELEGRAM_TOKEN está vacía o no existe en Railway.")
        
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("programar", programar_hora))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    
    restaurar_alarmas(app)
    
    print("🔮 El bot de Mozárabe Tarot en la nube está en marcha...")
    app.run_polling()

if __name__ == '__main__':
    main()