import json
import random
import logging
import os
import pytz
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
        [InlineKeyboardButton("🃏 Tirada de 3 Cartas", callback_data='menu_tres_cartas')],
        [InlineKeyboardButton("🧿 Significado de los Arcanos", callback_data='ver_arcanos')]
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

# Función auxiliar para generar textos e información de cartas (Mejorada con rotación)
def generar_datos_carta_aleatoria():
    claves_cartas = list(tarot_db.keys())
    carta_id = random.choice(claves_cartas)
    carta = tarot_db[carta_id]
    esta_invertida = random.choice([True, False])
    
    nombre = carta["nombre"]
    if esta_invertida:
        titulo = f"🃏 **{nombre}** (Invertida 🙃)"
        interpretacion = carta["significado_invertido"]
    else:
        titulo = f"🃏 **{nombre}** (Al Derecho ⭐)"
        interpretacion = carta["significado_derecho"]
        
    texto_final = f"{titulo}\n\n**Interpretación:**\n{interpretacion}"
    ruta_imagen = f"imagenes/{carta_id}.jpg"
    return texto_final, ruta_imagen, carta_id, esta_invertida

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje = (
        f"¡Hola, {usuario}! 🔮 Bienvenido a **Mozárabe Tarot**.\n\n"
        "Puedes pedir una carta como tirada del día, tirada de tres cartas, o programar tu carta diaria usando el comando:\n"
        "`/programar HH:MM` en formato 24 horas. (Ejemplo: `/programar 08:30`)\n\n"
        "¿Qué deseas consultar hoy?"
    )
    await update.message.reply_text(
        text=mensaje, 
        reply_markup=obtener_menu_principal(), 
        parse_mode="Markdown"
    )

# Función que se ejecuta automáticamente a la hora programada
async def enviar_carta_automatica(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id
    
    texto_final, ruta_imagen, carta_id, esta_invertida = generar_datos_carta_aleatoria()
    texto_automatico = f"🔮 **¡Tu carta del día automática ha llegado!** 🔮\n\n{texto_final}"
    
    try:
        if esta_invertida:
            imagen_original = Image.open(ruta_imagen)
            imagen_girada = imagen_original.rotate(180)
            memoria = io.BytesIO()
            memoria.name = 'girada.jpg'
            imagen_girada.save(memoria, 'JPEG')
            memoria.seek(0)
            await context.bot.send_photo(chat_id=chat_id, photo=memoria, caption=texto_automatico, parse_mode="Markdown")
        else:
            with open(ruta_imagen, 'rb') as foto:
                await context.bot.send_photo(chat_id=chat_id, photo=foto, caption=texto_automatico, parse_mode="Markdown")
    except FileNotFoundError:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_automatico}", parse_mode="Markdown")

# Comando /programar para que el usuario elija su hora
async def programar_hora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_message.chat_id
    usuario = update.effective_user.first_name
    
    if context.job_queue is None:
        await update.effective_message.reply_text(
            "❌ Error interno: El sistema de horarios (JobQueue) no está activo."
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
            "❌ Formato incorrecto. Por favor usa el comando de esta forma:\n"
            "`/programar HH:MM` (en formato de 24 horas, ej: `/programar 07:15`)"
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
        # Blindaje: Si venimos de una foto (Tirada del día), borramos y enviamos un texto fresco
        if query.message.photo:
            await query.message.delete()
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
        # Blindaje: Evitamos el error de intentar editar un mensaje que contiene foto
        if query.message.photo:
            await query.message.delete()
            mensaje_espera = await context.bot.send_message(
                chat_id=chat_id,
                text="🔮 Mezclando el mazo y sacando tus 3 cartas..."
            )
        else:
            mensaje_espera = await query.edit_message_text(
                text="🔮 Mezclando el mazo y sacando tus 3 cartas..."
            )
        
        # 1. Sacamos 3 números (llaves) al azar de la base de datos
        claves_cartas = list(tarot_db.keys())
        cartas_seleccionadas = random.sample(claves_cartas, 3)
        
        posiciones = ["Pasado 🕰️", "Presente 👁️", "Futuro ✨"]
        texto_lectura = "🌟 <b>TU TIRADA DE 3 CARTAS</b> 🌟\n\n"
        
        # 2. Enviamos las imágenes y construimos el texto
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
            try:
                if esta_invertida:
                    imagen_original = Image.open(ruta_imagen)
                    imagen_girada = imagen_original.rotate(180)
                    memoria = io.BytesIO()
                    memoria.name = 'girada.jpg'
                    imagen_girada.save(memoria, 'JPEG')
                    memoria.seek(0)
                    await context.bot.send_photo(chat_id=chat_id, photo=memoria)
                else:
                    with open(ruta_imagen, 'rb') as foto:
                        await context.bot.send_photo(chat_id=chat_id, photo=foto)
            except Exception as e:
                print(f"Error procesando la imagen {ruta_imagen}: {e}")
                pass 
            
            texto_lectura += f"📍 <b>{posicion}: {titulo_carta}</b>\n"
            texto_lectura += f"📖 <i>{significado}</i>\n\n"
            
        # Borramos el mensaje temporal de "Mezclando..." para dejar el chat impecable
        try:
            await mensaje_espera.delete()
        except Exception:
            pass

        # 3. Enviamos la interpretación final abajo de las fotos y anexamos de nuevo el menú principal
        await context.bot.send_message(
            chat_id=chat_id,
            text=texto_lectura,
            parse_mode="HTML",
            reply_markup=obtener_menu_principal()
        )

    # --- MENÚ DE INICIO ---
    elif query.data == 'volver_inicio':
        usuario = update.effective_user.first_name
        mensaje = (
            f"¡Hola, {usuario}! 🔮 Bienvenido a **Mozárabe Tarot**.\n\n"
            "Puedes pedir una carta como tirada del día, tirada de tres cartas, o programar tu carta diaria usando el comando:\n"
            "`/programar HH:MM`\n\n"
            "¿Qué deseas consultar hoy?"
        )
        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text(text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="Markdown")
        else:
            await query.message.edit_text(text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="Markdown")

    # --- TIRADA DEL DÍA ---
    elif query.data == 'tirada_dia':
        await query.message.delete()
        texto_final, ruta_imagen, carta_id, esta_invertida = generar_datos_carta_aleatoria()
        texto_dia = f"🌟 *TU CARTA DEL DÍA* 🌟\n\n{texto_final}"
        
        try:
            if esta_invertida:
                imagen_original = Image.open(ruta_imagen)
                imagen_girada = imagen_original.rotate(180)
                memoria = io.BytesIO()
                memoria.name = 'girada.jpg'
                imagen_girada.save(memoria, 'JPEG')
                memoria.seek(0)
                await query.message.reply_photo(photo=memoria, caption=texto_dia, parse_mode="Markdown", reply_markup=obtener_menu_principal())
            else:
                with open(ruta_imagen, 'rb') as foto:
                    await query.message.reply_photo(photo=foto, caption=texto_dia, parse_mode="Markdown", reply_markup=obtener_menu_principal())
        except FileNotFoundError:
            await query.message.reply_text(text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_dia}", parse_mode="Markdown", reply_markup=obtener_menu_principal())

    # --- CATEGORÍAS DE DICCIONARIO ---
    elif query.data == 'ver_arcanos':
        texto_menu = "🧿 **Significado de Arcanos**\n\n¿Qué grupo de cartas deseas consultar hoy?"
        if query.message.photo:
            await query.message.delete()
            await query.message.reply_text(text=texto_menu, reply_markup=obtener_menu_categorias(), parse_mode="Markdown")
        else:
            await query.message.edit_text(text=texto_menu, reply_markup=obtener_menu_categorias(), parse_mode="Markdown")

    elif query.data == 'cat_mayores':
        await query.message.edit_text(text="🃏 **Arcanos Mayores**\n\nSelecciona el arcano que deseas estudiar:", reply_markup=obtener_botones_mayores(), parse_mode="Markdown")

    elif query.data == 'cat_menores':
        await query.message.edit_text(text="🌿 **Arcanos Menores**\n\nSelecciona el palo que deseas consultar:", reply_markup=obtener_menu_palos(), parse_mode="Markdown")

    # --- PALOS ESPECÍFICOS ---
    elif query.data == 'palo_bastos':
        await query.message.edit_text(text="🪵 **Palo de Bastos** (Acción y Energía):", reply_markup=obtener_botones_menores(22, 35))

    elif query.data == 'palo_copas':
        await query.message.edit_text(text="🏆 **Palo de Copas** (Emociones y Amor):", reply_markup=obtener_botones_menores(36, 49))

    elif query.data == 'palo_espadas':
        await query.message.edit_text(text="⚔️ **Palo de Espadas** (Mente y Conflictos):", reply_markup=obtener_botones_menores(50, 63))

    elif query.data == 'palo_oros':
        await query.message.edit_text(text="🪙 **Palo de Oros** (Mundo Material y Finanzas):", reply_markup=obtener_botones_menores(64, 77))

    # --- MOSTRAR INFORMACIÓN DE CARTA SELECCIONADA ---
    elif query.data.startswith('info_'):
        carta_id = query.data.split('_')[1]
        carta = tarot_db[carta_id]
        texto_info = (
            f"🔮 **{carta['nombre']}**\n\n"
            f"🟢 **Al Derecho:**\n{carta['significado_derecho']}\n\n"
            f"🔴 **Invertida:**\n{carta['significado_invertido']}"
        )
        
        await query.message.delete()
        ruta_imagen = f"imagenes/{carta_id}.jpg"
        try:
            with open(ruta_imagen, 'rb') as foto:
                await query.message.reply_photo(photo=foto, caption=texto_info, parse_mode="Markdown", reply_markup=obtener_menu_principal())
        except FileNotFoundError:
            await query.message.reply_text(text=f"⚠️ (No se encontró la imagen {carta_id}.jpg)\n\n{texto_info}", parse_mode="Markdown", reply_markup=obtener_menu_principal())

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