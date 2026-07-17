import json
import random
import logging
import os
from zoneinfo import ZoneInfo
from datetime import time
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import io
from PIL import Image

# Configuración de registros
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Cargar la base de datos
with open('tarot_db.json', 'r', encoding='utf-8') as f:
    tarot_db = json.load(f)

def obtener_menu_principal():
    keyboard = [
        [InlineKeyboardButton("🃏 Tirada del Día (1 carta)", callback_data='tirada_dia')],
        [InlineKeyboardButton("⏰ Programar Carta Diaria", callback_data='menu_programar')],
        [InlineKeyboardButton("🎲 Tirada de 3 Cartas", callback_data='menu_tres_cartas')],
        [InlineKeyboardButton("🧿 Significado de los Arcanos", callback_data='ver_arcanos')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Menú para elegir entre Mayores o Menores
def obtener_menu_categorias():
    keyboard = [
        [InlineKeyboardButton("🪄 Arcanos Mayores", callback_data='cat_mayores')],
        [InlineKeyboardButton("🪆 Arcanos Menores", callback_data='cat_menores')],
        [InlineKeyboardButton("⬆️ Volver al Menú Principal", callback_data='volver_inicio')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Menú para elegir el palo de los Arcanos Menores
def obtener_menu_palos():
    keyboard = [
        [InlineKeyboardButton("🪵 Bastos", callback_data='palo_bastos'),
         InlineKeyboardButton("🥂 Copas", callback_data='palo_copas')],
        [InlineKeyboardButton("⚔️ Espadas", callback_data='palo_espadas'),
         InlineKeyboardButton("🪙 Oros", callback_data='palo_oros')],
        [InlineKeyboardButton("⬅️ Atrás", callback_data='ver_arcanos')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Genera botones para los 22 Arcanos Mayores
def obtener_botones_mayores():
    keyboard = []
    fila = []
    for i in range(22):
        nombre_corto = tarot_db[str(i)]["nombre"].split(" (")[0]
        fila.append(InlineKeyboardButton(nombre_corto, callback_data=f"info_{i}"))
        if len(fila) == 2:
            keyboard.append(fila)
            fila = []
    if fila:
        keyboard.append(fila)
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data='ver_arcanos')])
    return InlineKeyboardMarkup(keyboard)

# Genera botones para un palo específico de Arcanos Menores
def obtener_botones_menores(rango_inicio, rango_fin):
    keyboard = []
    fila = []
    for i in range(rango_inicio, rango_fin + 1):
        nombre_corto = tarot_db[str(i)]["nombre"]
        nombre_corto = nombre_corto.replace(" de Bastos", "").replace(" de Copas", "").replace(" de Espadas", "").replace(" de Oros", "")
        fila.append(InlineKeyboardButton(nombre_corto, callback_data=f"info_{i}"))
        if len(fila) == 3:
            keyboard.append(fila)
            fila = []
    if fila:
        keyboard.append(fila)
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data='cat_menores')])
    return InlineKeyboardMarkup(keyboard)

# Función auxiliar para generar textos e información de cartas
def generar_datos_carta_aleatoria():
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
    ruta_imagen = f"imagenes/{carta_id}.jpg"
    return texto_final, ruta_imagen, carta_id, esta_invertida

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje = (
        f"¡Hola, {usuario}! 🔮 Bienvenido a <b>Mozárabe Tarot</b>.\n\n"
        "Puedes pedir una carta como tirada del día, tirada de tres cartas, o programar tu carta diaria usando el comando:\n"
        "<code>/programar HH:MM</code> en formato 24 horas. (Ejemplo: <code>/programar 08:30</code>)\n\n"
        "¿Qué deseas consultar hoy?"
    )
    await update.message.reply_text(
        text=mensaje, 
        reply_markup=obtener_menu_principal(), 
        parse_mode="HTML"
    )

# Función que se ejecuta automáticamente a la hora programada
async def enviar_carta_automatica(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    
    texto_final, ruta_imagen, carta_id, esta_invertida = generar_datos_carta_aleatoria()
    texto_automatico = f"🔮 <b>¡Tu carta del día automática ha llegado!</b> 🔮\n\n{texto_final}"
    
    try:
        if esta_invertida:
            with Image.open(ruta_imagen) as imagen_original:
                imagen_girada = imagen_original.rotate(180)
                memoria = io.BytesIO()
                memoria.name = 'girada.jpg'
                imagen_girada.save(memoria, 'JPEG')
                memoria.seek(0)
                await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_automatico, parse_mode="HTML")
        else:
            with open(ruta_imagen, 'rb') as foto:
                await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_automatico, parse_mode="HTML")
    except FileNotFoundError:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_automatico}", parse_mode="HTML")

# Comando /programar para que el usuario elija su hora
async def programar_hora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    usuario = update.effective_user.first_name
    
    if context.job_queue is None:
        await update.effective_message.reply_text(
            "❌ Error interno: El sistema de horarios (JobQueue) no está activo. Asegúrate de tener instalado python-telegram-bot[job-queue]."
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
        
        context.job_queue.run_daily(
            enviar_carta_automatica,
            time=hora_programada,
            chat_id=chat_id,
            name=nombre_tarea
        )
        
        await update.effective_message.reply_text(
            f"✅ ¡Perfecto, {usuario}! He programado tu lectura diaria para las <b>{hora_texto}</b> todos los días.",
            reply_markup=obtener_menu_principal(),
            parse_mode="HTML"
        )
        
    except (IndexError, ValueError):
        await update.effective_message.reply_text(
            "❌ Formato incorrecto. Por favor usa el comando de esta forma:\n"
            "<code>/programar HH:MM</code> (en formato de 24 horas, ej: <code>/programar 07:15</code>)",
            parse_mode="HTML"
        )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    chat_id = update.effective_chat.id

    # --- CONFIGURAR ALARMA ---
    if query.data == 'menu_programar':
        mensaje_instrucciones = (
            "⏰ <b>Configuración de tu Alarma Diaria</b>\n\n"
            "Para recibir tu carta automáticamente, escribe en el chat el comando <code>/programar</code> seguido de la hora.\n\n"
            "👉 <b>Ejemplo:</b> <code>/programar 08:30</code>"
        )
        if query.message.photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=chat_id,
                text=mensaje_instrucciones,
                parse_mode="HTML",
                reply_markup=obtener_menu_principal()
            )
        else:
            await query.message.edit_text(
                text=mensaje_instrucciones,
                parse_mode="HTML",
                reply_markup=obtener_menu_principal()
            )

    # --- TIRADA DE 3 CARTAS ---
    elif query.data == "menu_tres_cartas":
        if query.message.photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            mensaje_espera = await context.bot.send_message(
                chat_id=chat_id,
                text="🔮 Mezclando el mazo y sacando tus 3 cartas..."
            )
        else:
            mensaje_espera = await query.edit_message_text(
                text="🔮 Mezclando el mazo y sacando tus 3 cartas..."
            )
        
        claves_cartas = list(tarot_db.keys())
        cartas_seleccionadas = random.sample(claves_cartas, 3)
        posiciones = ["Pasado 🕰️", "Presente 👁️", "Futuro ✨"]
        
        # Enviar cada carta con su interpretación como pie de foto
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
            
            ruta_imagen = f"imagenes/{clave}.jpg" 
            texto_lectura = f"📌 <b>{posicion}: {titulo_carta}</b>\n\n📖 <i>{significado}</i>"
            
            # Solo la última carta llevará el menú principal para no inundar el chat de botones
            teclado = obtener_menu_principal() if i == 2 else None
            
            try:
                if esta_invertida:
                    with Image.open(ruta_imagen) as imagen_original:
                        imagen_girada = imagen_original.rotate(180)
                        memoria = io.BytesIO()
                        memoria.name = 'girada.jpg'
                        imagen_girada.save(memoria, 'JPEG')
                        memoria.seek(0)
                        await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_lectura, parse_mode="HTML", reply_markup=teclado)
                else:
                    with open(ruta_imagen, 'rb') as foto:
                        await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_lectura, parse_mode="HTML", reply_markup=teclado)
            except Exception as e:
                print(f"Error procesando la imagen {ruta_imagen}: {e}")
                await context.bot.send_message(chat_id=chat_id, text=texto_lectura, parse_mode="HTML", reply_markup=teclado)
            
        try:
            await mensaje_espera.delete()
        except Exception:
            pass

    # --- MENÚ DE INICIO ---
    elif query.data == 'volver_inicio':
        usuario = update.effective_user.first_name
        mensaje = (
            f"¡Hola, {usuario}! 🔮 Bienvenido a <b>Mozárabe Tarot</b>.\n\n"
            "Puedes pedir una carta como tirada del día, tirada de tres cartas, o programar tu carta diaria usando el comando:\n"
            "<code>/programar HH:MM</code>\n\n"
            "¿Qué deseas consultar hoy?"
        )
        if query.message.photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(chat_id=chat_id, text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="HTML")
        else:
            await query.message.edit_text(text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="HTML")

    # --- TIRADA DEL DÍA ---
    elif query.data == 'tirada_dia':
        try:
            await query.message.delete()
        except Exception:
            pass
            
        texto_final, ruta_imagen, carta_id, esta_invertida = generar_datos_carta_aleatoria()
        texto_dia = f"🌟 <b>TU CARTA DEL DÍA</b> 🌟\n\n{texto_final}"
        
        try:
            if esta_invertida:
                with Image.open(ruta_imagen) as imagen_original:
                    imagen_girada = imagen_original.rotate(180)
                    memoria = io.BytesIO()
                    memoria.name = 'girada.jpg'
                    imagen_girada.save(memoria, 'JPEG')
                    memoria.seek(0)
                    await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_dia, parse_mode="HTML", reply_markup=obtener_menu_principal())
            else:
                with open(ruta_imagen, 'rb') as foto:
                    await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_dia, parse_mode="HTML", reply_markup=obtener_menu_principal())
        except FileNotFoundError:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_dia}", parse_mode="HTML", reply_markup=obtener_menu_principal())

    # --- CATEGORÍAS DE DICCIONARIO ---
    elif query.data == 'ver_arcanos':
        texto_menu = "🧿 <b>Significado de Arcanos</b>\n\n¿Qué grupo de cartas deseas consultar hoy?"
        if query.message.photo:
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(chat_id=chat_id, text=texto_menu, reply_markup=obtener_menu_categorias(), parse_mode="HTML")
        else:
            await query.message.edit_text(text=texto_menu, reply_markup=obtener_menu_categorias(), parse_mode="HTML")

    elif query.data == 'cat_mayores':
        await query.message.edit_text(text="🪄 <b>Arcanos Mayores</b>\n\nSelecciona el arcano que deseas estudiar:", reply_markup=obtener_botones_mayores(), parse_mode="HTML")

    elif query.data == 'cat_menores':
        await query.message.edit_text(text="🪆 <b>Arcanos Menores</b>\n\nSelecciona el palo que deseas consultar:", reply_markup=obtener_menu_palos(), parse_mode="HTML")

    # --- PALOS ESPECÍFICOS ---
    elif query.data == 'palo_bastos':
        await query.message.edit_text(text="🪵 <b>Palo de Bastos</b> (Acción y Energía):", reply_markup=obtener_botones_menores(22, 35), parse_mode="HTML")

    elif query.data == 'palo_copas':
        await query.message.edit_text(text="🥂 <b>Palo de Copas</b> (Emociones y Amor):", reply_markup=obtener_botones_menores(36, 49), parse_mode="HTML")

    elif query.data == 'palo_espadas':
        await query.message.edit_text(text="⚔️ <b>Palo de Espadas</b> (Mente y Conflictos):", reply_markup=obtener_botones_menores(50, 63), parse_mode="HTML")

    elif query.data == 'palo_oros':
        await query.message.edit_text(text="🪙 <b>Palo de Oros</b> (Mundo Material y Finanzas):", reply_markup=obtener_botones_menores(64, 77), parse_mode="HTML")

    # --- MOSTRAR INFORMACIÓN DE CARTA SELECCIONADA ---
    elif query.data.startswith('info_'):
        carta_id = query.data.split('_')[1]
        carta = tarot_db[carta_id]
        texto_info = (
            f"🔮 <b>{carta['nombre']}</b>\n\n"
            f"🟢 <b>Al Derecho:</b>\n{carta['significado_derecho']}\n\n"
            f"🔴 <b>Invertida:</b>\n{carta['significado_invertido']}"
        )
        
        try:
            await query.message.delete()
        except Exception:
            pass
            
        ruta_imagen = f"imagenes/{carta_id}.jpg"
        try:
            with open(ruta_imagen, 'rb') as foto:
                await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_info, parse_mode="HTML", reply_markup=obtener_menu_principal())
        except FileNotFoundError:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_info}", parse_mode="HTML", reply_markup=obtener_menu_principal())

def main():
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    if not TOKEN:
        raise ValueError("❌ ERROR: La variable de entorno TELEGRAM_TOKEN está vacía o no existe en Railway.")
        
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("programar", programar_hora))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    
    print("🔮 El bot del Tarot de Marsella en la nube está en marcha...")
    app.run_polling()

if __name__ == '__main__':
    main()