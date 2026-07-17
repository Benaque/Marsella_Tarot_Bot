import json
import random
import logging
import os
import asyncio
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import io
from PIL import Image

# Configuración de registros
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Variables globales
tarot_db = None

def load_tarot_db():
    """Carga la base de datos de forma segura"""
    global tarot_db
    try:
        with open('tarot_db.json', 'r', encoding='utf-8') as f:
            tarot_db = json.load(f)
        logging.info(f"Base de datos Tarot cargada correctamente: {len(tarot_db)} cartas")
    except FileNotFoundError:
        logging.error("❌ No se encontró el archivo tarot_db.json")
        raise
    except Exception as e:
        logging.error(f"❌ Error al cargar tarot_db.json: {e}")
        raise


def obtener_menu_principal():
    keyboard = [
        [InlineKeyboardButton("🃏 Tirada del Día (1 carta)", callback_data='tirada_dia')],
        [InlineKeyboardButton("⏰ Programar Carta Diaria", callback_data='menu_programar')],
        [InlineKeyboardButton("🃏 Tirada de 3 Cartas", callback_data='menu_tres_cartas')],
        [InlineKeyboardButton("🧿 Significado de los Arcanos", callback_data='ver_arcanos')]
    ]
    return InlineKeyboardMarkup(keyboard)


def obtener_menu_categorias():
    keyboard = [
        [InlineKeyboardButton("🃏 Arcanos Mayores", callback_data='cat_mayores')],
        [InlineKeyboardButton("🌿 Arcanos Menores", callback_data='cat_menores')],
        [InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data='volver_inicio')]
    ]
    return InlineKeyboardMarkup(keyboard)


def obtener_menu_palos():
    keyboard = [
        [InlineKeyboardButton("🪵 Bastos", callback_data='palo_bastos'),
         InlineKeyboardButton("🏆 Copas", callback_data='palo_copas')],
        [InlineKeyboardButton("⚔️ Espadas", callback_data='palo_espadas'),
         InlineKeyboardButton("🪙 Oros", callback_data='palo_oros')],
        [InlineKeyboardButton("⬅️ Atrás", callback_data='ver_arcanos')]
    ]
    return InlineKeyboardMarkup(keyboard)


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


def obtener_botones_menores(rango_inicio, rango_fin):
    keyboard = []
    fila = []
    for i in range(rango_inicio, rango_fin + 1):
        nombre_corto = tarot_db[str(i)]["nombre"]
        nombre_corto = nombre_corto.replace(" de Bastos", "").replace(" de Copas", "") \
                                   .replace(" de Espadas", "").replace(" de Oros", "")
        fila.append(InlineKeyboardButton(nombre_corto, callback_data=f"info_{i}"))
        if len(fila) == 3:
            keyboard.append(fila)
            fila = []
    if fila:
        keyboard.append(fila)
    keyboard.append([InlineKeyboardButton("⬅️ Atrás", callback_data='cat_menores')])
    return InlineKeyboardMarkup(keyboard)


def generar_datos_carta_aleatoria():
    """Genera una carta aleatoria con orientación"""
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


async def send_card_photo(chat_id: int, bot, ruta_imagen: str, caption: str, esta_invertida: bool):
    """Helper reutilizable para enviar cartas con o sin inversión"""
    try:
        if esta_invertida:
            imagen_original = Image.open(ruta_imagen)
            imagen_girada = imagen_original.rotate(180, expand=True)
            memoria = io.BytesIO()
            memoria.name = 'girada.jpg'
            imagen_girada.save(memoria, 'JPEG')
            memoria.seek(0)
            await bot.send_photo(chat_id=chat_id, photo=memoria, caption=caption, parse_mode="Markdown")
        else:
            with open(ruta_imagen, 'rb') as foto:
                await bot.send_photo(chat_id=chat_id, photo=foto, caption=caption, parse_mode="Markdown")
    except FileNotFoundError:
        await bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ (No se encontró la imagen {ruta_imagen})\n\n{caption}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Error procesando imagen {ruta_imagen}: {e}")
        await bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")


# ==================== HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje = (
        f"¡Hola, {usuario}! 🔮 Bienvenido a **Mozárabe Tarot**.\n\n"
        "Puedes pedir una carta como tirada del día, tirada de tres cartas, o programar tu carta diaria.\n\n"
        "¿Qué deseas consultar hoy?"
    )
    await update.message.reply_text(
        text=mensaje,
        reply_markup=obtener_menu_principal(),
        parse_mode="Markdown"
    )


async def enviar_carta_automatica(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    chat_id = job.chat_id

    texto_final, ruta_imagen, carta_id, esta_invertida = generar_datos_carta_aleatoria()
    texto_automatico = f"🔮 **¡Tu carta del día automática ha llegado!** 🔮\n\n{texto_final}"

    await send_card_photo(chat_id, context.bot, ruta_imagen, texto_automatico, esta_invertida)


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

        # Eliminar jobs anteriores
        nombre_tarea = f"tarot_{chat_id}"
        for job in context.job_queue.get_jobs_by_name(nombre_tarea):
            job.schedule_removal()

        # Programar nuevo job
        tz = ZoneInfo("America/Mexico_City")
        hora_programada = time(hour=hora, minute=minuto, tzinfo=tz)

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
            "❌ Formato incorrecto.\n\n"
            "Usa: `/programar HH:MM`\n"
            "Ejemplo: `/programar 08:30`",
            parse_mode="Markdown"
        )


async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    bot = context.bot

    # ==================== MENÚ PROGRAMAR ====================
    if query.data == 'menu_programar':
        mensaje = (
            "⏰ <b>Configuración de tu Alarma Diaria</b>\n\n"
            "Escribe el comando:\n"
            "<code>/programar HH:MM</code>\n\n"
            "👉 Ejemplo: <code>/programar 08:30</code>"
        )
        if query.message and query.message.photo:
            await query.message.delete()
            await bot.send_message(chat_id=chat_id, text=mensaje, parse_mode="HTML", reply_markup=obtener_menu_principal())
        else:
            await query.message.edit_text(text=mensaje, parse_mode="HTML", reply_markup=obtener_menu_principal())

    # ==================== TIRADA DE 3 CARTAS ====================
    elif query.data == "menu_tres_cartas":
        if query.message and query.message.photo:
            await query.message.delete()
        else:
            await query.message.edit_text("🔮 Mezclando el mazo y sacando tus 3 cartas...")

        claves_cartas = list(tarot_db.keys())
        cartas_seleccionadas = random.sample(claves_cartas, 3)
        posiciones = ["Pasado 🕰️", "Presente 👁️", "Futuro ✨"]
        texto_lectura = "🌟 <b>TU TIRADA DE 3 CARTAS</b> 🌟\n\n"

        for i, clave in enumerate(cartas_seleccionadas):
            datos = tarot_db[clave]
            esta_invertida = random.choice([True, False])
            titulo = f"{datos['nombre']} (Invertida 🙃)" if esta_invertida else f"{datos['nombre']} (Al derecho ⭐)"
            significado = datos['significado_invertido'] if esta_invertida else datos['significado_derecho']
            ruta = f"imagenes/{clave}.jpg"

            await send_card_photo(chat_id, bot, ruta, "", esta_invertida)

            texto_lectura += f"📍 <b>{posiciones[i]}: {titulo}</b>\n"
            texto_lectura += f"📖 <i>{significado}</i>\n\n"

        await bot.send_message(
            chat_id=chat_id,
            text=texto_lectura,
            parse_mode="HTML",
            reply_markup=obtener_menu_principal()
        )

    # ==================== VOLVER AL INICIO ====================
    elif query.data == 'volver_inicio':
        usuario = update.effective_user.first_name
        mensaje = (
            f"¡Hola, {usuario}! 🔮 Bienvenido a **Mozárabe Tarot**.\n\n"
            "¿Qué deseas consultar hoy?"
        )
        if query.message and query.message.photo:
            await query.message.delete()
            await bot.send_message(chat_id=chat_id, text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="Markdown")
        else:
            await query.message.edit_text(text=mensaje, reply_markup=obtener_menu_principal(), parse_mode="Markdown")

    # ==================== TIRADA DEL DÍA ====================
    elif query.data == 'tirada_dia':
        if query.message:
            await query.message.delete()
        texto_final, ruta_imagen, carta_id, esta_invertida = generar_datos_carta_aleatoria()
        texto_dia = f"🌟 *TU CARTA DEL DÍA* 🌟\n\n{texto_final}"
        await send_card_photo(chat_id, bot, ruta_imagen, texto_dia, esta_invertida)

    # ==================== DICCIONARIO DE ARCANO ====================
    elif query.data == 'ver_arcanos':
        texto = "🧿 **Significado de Arcanos**\n\n¿Qué grupo de cartas deseas consultar hoy?"
        if query.message and query.message.photo:
            await query.message.delete()
            await bot.send_message(chat_id=chat_id, text=texto, reply_markup=obtener_menu_categorias(), parse_mode="Markdown")
        else:
            await query.message.edit_text(text=texto, reply_markup=obtener_menu_categorias(), parse_mode="Markdown")

    elif query.data == 'cat_mayores':
        await query.message.edit_text(
            text="🃏 **Arcanos Mayores**\n\nSelecciona el arcano que deseas estudiar:",
            reply_markup=obtener_botones_mayores(),
            parse_mode="Markdown"
        )

    elif query.data == 'cat_menores':
        await query.message.edit_text(
            text="🌿 **Arcanos Menores**\n\nSelecciona el palo que deseas consultar:",
            reply_markup=obtener_menu_palos(),
            parse_mode="Markdown"
        )

    elif query.data.startswith('palo_'):
        palos = {
            'palo_bastos': ("🪵 **Palo de Bastos** (Acción y Energía):", 22, 35),
            'palo_copas': ("🏆 **Palo de Copas** (Emociones y Amor):", 36, 49),
            'palo_espadas': ("⚔️ **Palo de Espadas** (Mente y Conflictos):", 50, 63),
            'palo_oros': ("🪙 **Palo de Oros** (Mundo Material y Finanzas):", 64, 77),
        }
        texto, inicio, fin = palos[query.data]
        await query.message.edit_text(text=texto, reply_markup=obtener_botones_menores(inicio, fin))

    elif query.data.startswith('info_'):
        carta_id = query.data.split('_')[1]
        carta = tarot_db[carta_id]
        texto_info = (
            f"🔮 **{carta['nombre']}**\n\n"
            f"🟢 **Al Derecho:**\n{carta['significado_derecho']}\n\n"
            f"🔴 **Invertida:**\n{carta['significado_invertido']}"
        )
        if query.message:
            await query.message.delete()
        ruta_imagen = f"imagenes/{carta_id}.jpg"
        await send_card_photo(chat_id, bot, ruta_imagen, texto_info, False)


def main():
    load_tarot_db()

    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("❌ ERROR: La variable de entorno TELEGRAM_TOKEN no está configurada.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("programar", programar_hora))
    app.add_handler(CallbackQueryHandler(manejar_botones))

    print("🔮 El bot de Mozárabe Tarot está en marcha...")
    app.run_polling()


if __name__ == '__main__':
    main()