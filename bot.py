import json
import random
import logging
import os  # 👈 ¡ESTA ES LA LÍNEA QUE FALTA!
import pytz
from datetime import time
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

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
        [InlineKeyboardButton("🃏 Tirada de 3 Cartas", callback_data='menu_tres_cartas')],
        [InlineKeyboardButton("🔮 Significado de los Arcanos", callback_data='ver_arcanos')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Menú para elegir entre Mayores o Menores
def obtener_menu_categorias():
    keyboard = [
        [InlineKeyboardButton("🃏 Arcanos Mayores", callback_data='cat_mayores')],
        [InlineKeyboardButton("🌿 Arcanos Menores", callback_data='cat_menores')],
        [InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data='volver_inicio')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Menú para elegir el palo de los Arcanos Menores
def obtener_menu_palos():
    keyboard = [
        [InlineKeyboardButton("🪵 Bastos", callback_data='palo_bastos'),
         InlineKeyboardButton("🏆 Copas", callback_data='palo_copas')],
        [InlineKeyboardButton("⚔️ Espadas", callback_data='palo_espadas'),
         InlineKeyboardButton("🪙 Oros", callback_data='palo_oros')],
        [InlineKeyboardButton("⬅️ Atrás", callback_data='ver_arcanos')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Genera botones para los 22 Arcanos Mayores (en filas de 2 botones)
def obtener_botones_mayores():
    keyboard = []
    fila = []
    for i in range(22):
        nombre_corto = tarot_db[str(i)]["nombre"].split(" (")[0] # Simplifica el nombre para que quepa en el botón
        fila.append(InlineKeyboardButton(nombre_corto, callback_data=f"info_{i}"))
        if len(fila) == 2:
            keyboard.append(fila)
            fila = []
    if fila:
        keyboard.append(fila)
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data='ver_arcanos')])
    return InlineKeyboardMarkup(keyboard)

# Genera botones para un palo específico de Arcanos Menores
# Bastos (22-35), Copas (36-49), Espadas (50-63), Oros (64-77)
def obtener_botones_menores(rango_inicio, rango_fin):
    keyboard = []
    fila = []
    for i in range(rango_inicio, rango_fin + 1):
        nombre_corto = tarot_db[str(i)]["nombre"]
        # Simplificar nombres largos (ej: "As de Bastos" -> "As")
        nombre_corto = nombre_corto.replace(" de Bastos", "").replace(" de Copas", "").replace(" de Espadas", "").replace(" de Oros", "")
        fila.append(InlineKeyboardButton(nombre_corto, callback_data=f"info_{i}"))
        if len(fila) == 3: # 3 botones por fila para que se vea ordenado en el móvil
            keyboard.append(fila)
            fila = []
    if fila:
        keyboard.append(fila)
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data='cat_menores')])
    return InlineKeyboardMarkup(keyboard)

# Función auxiliar para generar la tirada (NUEVO: Separada para reutilizarla)
def generar_texto_y_ruta_tirada():
    carta_id = str(random.randint(0, 77))
    carta = tarot_db[carta_id]
    al_derecho = random.choice([True, False])
    
    nombre = carta["nombre"]
    if al_derecho:
        titulo = f"🃏 **{nombre}** (Al Derecho)"
        interpretacion = carta["significado_derecho"]
    else:
        titulo = f"🃏 **{nombre}** (Invertida)"
        interpretacion = carta["significado_invertido"]
        
    texto_final = f"{titulo}\n\n**Interpretación:**\n{interpretacion}"
    ruta_imagen = f"imagenes/{carta_id}.jpg"
    return texto_final, ruta_imagen, carta_id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    
    # 🚨 Modificamos el texto para usar etiquetas HTML limpias
    mensaje = (
        f"¡Hola, {usuario}! 🔮 Bienvenido al <b>Tarot de Marsella</b>.\n\n"
        "Puedes pedir una carta en cualquier momento o programar tu carta diaria usando el comando:\n"
        "<code>/programar HH:MM</code> (Ejemplo: <code>/programar 08:30</code>)\n\n"
        "¿Qué deseas consultar hoy?"
    )
    
    # ✅ Cambiamos parse_mode a "HTML"
    await update.message.reply_text(
        text=mensaje, 
        reply_markup=obtener_menu_principal(), 
        parse_mode="HTML"
    )

# NUEVO: Función que se ejecuta automáticamente a la hora programada
async def enviar_carta_automatica(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    
    texto_final, ruta_imagen, carta_id = generar_texto_y_ruta_tirada()
    texto_automatico = f"🔮 **¡Tu Carta del Día Automática ha llegado!** 🔮\n\n{texto_final}"
    
    try:
        with open(ruta_imagen, 'rb') as foto:
            await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_automatico, parse_mode="Markdown")
    except FileNotFoundError:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_automatico}", parse_mode="Markdown")

# NUEVO: Comando /programar para que el usuario elija su hora
async def programar_hora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    usuario = update.effective_user.first_name
    
    # Verificación de seguridad por si el JobQueue no cargó en el sistema
    if context.job_queue is None:
        await update.effective_message.reply_text(
            "❌ Error interno: El sistema de horarios (JobQueue) no está activo en este servidor. "
            "Por favor, revisa la instalación de python-telegram-bot[job-queue]."
        )
        return

    try:
        # Extraer la hora del mensaje (ej: /programar 08:30 -> "08:30")
        hora_texto = context.args[0]
        hora_str, minuto_str = hora_texto.split(":")
        hora = int(hora_str)
        minuto = int(minuto_str)
        
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            raise ValueError
        
        # Eliminar tarea programada anterior si el usuario ya tenía una
        nombre_tarea = str(chat_id)
        tareas_actuales = context.job_queue.get_jobs_by_name(nombre_tarea)
        for tarea in tareas_actuales:
            tarea.schedule_removal()
            
        # Programar la nueva tarea diaria
       # Define tu zona horaria (por ejemplo, "America/Mexico_City" o tu zona local)
        zona_horaria = pytz.timezone("America/Mexico_City")
        # Programar la nueva tarea diaria con la zona horaria explícita
        hora_programada = time(hour=hora, minute=minuto, tzinfo=zona_horaria)
        context.job_queue.run_daily(
            enviar_carta_automatica,
            time=hora_programada,
            chat_id=chat_id,
            name=nombre_tarea
        )
        
        await update.effective_message.reply_text(
            f"✅ ¡Perfecto, {usuario}! He programado tu lectura diaria para las **{hora_texto}** todos los días."
        )
        
    except (IndexError, ValueError):
        await update.effective_message.reply_text(
            "❌ Formato incorrecto. Por favor usa el comando de esta forma:\n"
            "`/programar HH:MM` (en formato de 24 horas, ej: `/programar 07:15` o `/programar 21:00`)"
        )

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # Esto es vital: le dice a Telegram que ya recibimos el clic para que quite el "relojito" de carga
    await query.answer() 

    # Si el usuario hace clic en el botón de programar
    if query.data == "menu_programar":  
        mensaje = (
            "⏰ <b>Para programar tu carta diaria:</b>\n\n"
            "Escríbeme el comando <code>/programar</code> seguido de la hora en formato 24h.\n\n"
            "👉 Ejemplo: <code>/programar 08:30</code>"
        )
        await query.edit_message_text(text=mensaje, parse_mode="HTML")

    elif query.data == "menu_tres_cartas":
        # Le avisamos al usuario que estamos barajando
        await query.edit_message_text("🔮 Mezclando el mazo y sacando tus 3 cartas...")
        
        # 1. Sacamos 3 cartas distintas al azar de nuestra base de datos
        # Asumiendo que 'tarot_db' es el diccionario cargado desde tu JSON
        nombres_cartas = list(tarot_db.keys())
        cartas_seleccionadas = random.sample(nombres_cartas, 3)
        
        posiciones = ["Pasado 🕰️", "Presente 👁️", "Futuro ✨"]
        texto_lectura = "🌟 <b>TU TIRADA DE 3 CARTAS</b> 🌟\n\n"
        
        chat_id = update.effective_chat.id
        
        # 2. Enviamos las imágenes una por una y armamos el texto
        for i in range(3):
            nombre_carta = cartas_seleccionadas[i]
            datos_carta = tarot_db[nombre_carta]
            posicion = posiciones[i]
            
            # Enviamos la foto de la carta
            with open(datos_carta['imagen'], 'rb') as foto:
                await context.bot.send_photo(chat_id=chat_id, photo=foto)
                
            # Agregamos la información al mensaje final
            texto_lectura += f"📍 <b>{posicion}: {nombre_carta}</b>\n"
            texto_lectura += f"📖 <i>{datos_carta['significado']}</i>\n\n"
            
        # 3. Enviamos el mensaje con la interpretación completa
        await context.bot.send_message(
            chat_id=chat_id,
            text=texto_lectura,
            parse_mode="HTML"
        ) 

    # Aquí irían tus otros botones (sacar carta, ver diccionario, etc.)
    elif query.data == "sacar_carta":
        # ... tu código actual para sacar cartas ...
        pass

    # --- MENÚ DE INICIO ---
    if query.data == 'volver_inicio':
        usuario = update.effective_user.first_name
        mensaje = (
            f"¡Hola, {usuario}! 🔮 Bienvenido al **Tarot de Marsella**.\n\n"
            "Puedes pedir una carta en cualquier momento o programar tu carta diaria usando el comando:\n"
            "`/programar HH:MM`\n\n"
            "¿Qué deseas consultar hoy?"
        )
        # Si el mensaje anterior contenía una foto, lo borramos y enviamos uno nuevo
        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text(text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="Markdown")
        else:
            await query.message.edit_text(text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="Markdown")
        await query.answer()

    # --- TIRADA DEL DÍA ---
    elif query.data == 'tirada_dia':
        # Borramos el menú para enviar la foto fresca
        await query.message.delete()
        texto_final, ruta_imagen, carta_id = generar_texto_y_ruta_tirada()
        try:
            with open(ruta_imagen, 'rb') as foto:
                await query.message.reply_photo(photo=foto, caption=texto_final, parse_mode="Markdown", reply_markup=obtener_menu_principal())
            await query.answer()
        except FileNotFoundError:
            await query.message.reply_text(text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_final}", parse_mode="Markdown", reply_markup=obtener_menu_principal())
            await query.answer()

    # --- CONFIGURAR ALARMA ---
    elif query.data == 'menu_programar':
        mensaje_instrucciones = (
            "⏰ **Configuración de tu Alarma Diaria**\n\n"
            "Para recibir tu carta automáticamente, escribe en el chat el comando `/programar` seguido de la hora.\n\n"
            "👉 **Ejemplo:** `/programar 08:30`"
        )
        await query.message.edit_text(text=mensaje_instrucciones, parse_mode="Markdown", reply_markup=obtener_menu_principal())
        await query.answer()

# --- CATEGORÍAS DE DICCIONARIO ---
    elif query.data == 'ver_arcanos':
        texto_menu = "🔮 **Diccionario de Arcanos**\n\n¿Qué grupo de cartas deseas consultar hoy?"
        
        # Si venimos de ver una carta (que es una foto), borramos y enviamos texto fresco
        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text(
                text=texto_menu,
                reply_markup=obtener_menu_categorias(),
                parse_mode="Markdown"
            )
        else:
            # Si ya estábamos en un menú de texto, solo lo editamos fluidamente
            await query.message.edit_text(
                text=texto_menu,
                reply_markup=obtener_menu_categorias(),
                parse_mode="Markdown"
            )
        await query.answer()

    elif query.data == 'cat_mayores':
        await query.message.edit_text(
            text="🃏 **Arcanos Mayores**\n\nSelecciona el arcano que deseas estudiar:",
            reply_markup=obtener_botones_mayores(),
            parse_mode="Markdown"
        )
        await query.answer()

    elif query.data == 'cat_menores':
        await query.message.edit_text(
            text="🌿 **Arcanos Menores**\n\nSelecciona el palo que deseas consultar:",
            reply_markup=obtener_menu_palos(),
            parse_mode="Markdown"
        )
        await query.answer()

    # --- PALOS ESPECÍFICOS ---
    elif query.data == 'palo_bastos':
        await query.message.edit_text(text="🪵 **Palo de Bastos** (Acción y Energía):", reply_markup=obtener_botones_menores(22, 35))
        await query.answer()

    elif query.data == 'palo_copas':
        await query.message.edit_text(text="🏆 **Palo de Copas** (Emociones y Amor):", reply_markup=obtener_botones_menores(36, 49))
        await query.answer()

    elif query.data == 'palo_espadas':
        await query.message.edit_text(text="⚔️ **Palo de Espadas** (Mente y Conflictos):", reply_markup=obtener_botones_menores(50, 63))
        await query.answer()

    elif query.data == 'palo_oros':
        await query.message.edit_text(text="🪙 **Palo de Oros** (Mundo Material y Finanzas):", reply_markup=obtener_botones_menores(64, 77))
        await query.answer()

    # --- MOSTRAR INFORMACIÓN DE CARTA SELECCIONADA ---
    elif query.data.startswith('info_'):
        carta_id = query.data.split('_')[1]
        carta = tarot_db[carta_id]
        
        # Al consultar el diccionario, enviamos ambos significados a la vez
        texto_info = (
            f"🔮 **{carta['nombre']}**\n\n"
            f"🟢 **Al Derecho:**\n{carta['significado_derecho']}\n\n"
            f"🔴 **Invertida:**\n{carta['significado_invertido']}"
        )
        
        # Borramos el menú de selección para enviar la imagen de la carta consultada
        await query.message.delete()
        
        ruta_imagen = f"imagenes/{carta_id}.jpg"
        try:
            with open(ruta_imagen, 'rb') as foto:
                await query.message.reply_photo(
                    photo=foto,
                    caption=texto_info,
                    parse_mode="Markdown",
                    reply_markup=obtener_menu_principal()
                )
            await query.answer()
        except FileNotFoundError:
            await query.message.reply_text(
                text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_info}",
                parse_mode="Markdown",
                reply_markup=obtener_menu_principal()
            )
            await query.answer()


async def programar_hora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    usuario = update.effective_user.first_name
    
    if context.job_queue is None:
        await update.effective_message.reply_text(
            "❌ Error interno: El sistema de horarios (JobQueue) no está activo."
        )
        return

    try:
        # Lee la hora que el usuario escribió después de la palabra /programar
        hora_texto = context.args[0]
        hora_str, minuto_str = hora_texto.split(":")
        hora = int(hora_str)
        minuto = int(minuto_str)
        
        if not (0 <= hora <= 23 and 0 <= minuto <= 59):
            raise ValueError
        
        # Eliminar tarea anterior si existía
        nombre_tarea = str(chat_id)
        tareas_actuales = context.job_queue.get_jobs_by_name(nombre_tarea)
        for tarea in tareas_actuales:
            tarea.schedule_removal()
            
        # Programar la nueva tarea con tu zona horaria
        zona_horaria = pytz.timezone("America/Mexico_City") 
        hora_programada = time(hour=hora, minute=minuto, tzinfo=zona_horaria)
        
        context.job_queue.run_daily(
            enviar_carta_automatica,
            time=hora_programada,
            chat_id=chat_id,
            name=nombre_tarea
        )
        
        await update.effective_message.reply_text(
            f"✅ ¡Perfecto, {usuario}! He programado tu lectura diaria para las **{hora_texto}** todos los días.",
            reply_markup=obtener_menu_principal()
        )
        
    except (IndexError, ValueError):
        await update.effective_message.reply_text(
            "❌ Formato incorrecto. Por favor escribe el comando exactamente así:\n"
            "`/programar HH:MM` (Ejemplo: `/programar 07:15`)"
        )

def main():
    # Buscamos la variable
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    
    # 🚨 VALIDACIÓN CRÍTICA: Si es None o está vacío, detenemos el bot con un mensaje
    if not TOKEN:
        raise ValueError("❌ ERROR: La variable de entorno TELEGRAM_TOKEN está vacía o no existe en Railway.")
        
    # Si pasa la validación, construye la app
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("programar", programar_hora))
    app.add_handler(CallbackQueryHandler(manejar_botones))
    
    print("🔮 El bot del Tarot de Marsella en la nube está en marcha...")
    app.run_polling()

if __name__ == '__main__':
    main()