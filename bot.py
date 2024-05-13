import logging
import re
from telegram import Update, ForceReply, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import paramiko
import os
from dotenv import load_dotenv
import time
import psycopg2 as ps

load_dotenv()

LOG_DEST = os.getenv("PROJECT_DEST")
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO, filename=f'{LOG_DEST}/logfile.log' 
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")

HOST = os.getenv("RM_HOST")
PORT = os.getenv("RM_PORT")
USER_NAME = os.getenv("RM_USER")
PASSWORD = os.getenv("RM_PASSWORD")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_DATABASE")

def db_execute(command):
    res = "error"
    
    try:
        connection = ps.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT, 
            database=DB_NAME
        )

        cursor = connection.cursor()
        cursor.execute(command)
        res = ""

        data = cursor.fetchall()
        try:
            for row in data:
                res += row[1] + "\n"
        except:
            for row in data[-30:]:
                res += row[0] + "\n"

        logging.info(f"db command {command} executed")
    except (Exception, ps.Error) as error:
        logging.error("ERROR connection to PostgreSQL: %s", error)
    finally:
        if connection is not None:
            connection.commit()
            cursor.close()
            connection.close()
    
    return res

def messageSendMD(update: Update, msg):
    max_length = 4000

    if len(msg) <= max_length:
        update.message.reply_text("```"+msg+'```', parse_mode=ParseMode.MARKDOWN)
        return
    else:
        parts = []
        current_part = ''
        for char in msg:
            if len(current_part) + len(char) <= max_length:
                current_part += char
            else:
                parts.append(current_part)
                current_part = char
        if current_part:
            parts.append(current_part)

    for i in parts:
        update.message.reply_text("```"+i+'```', parse_mode=ParseMode.MARKDOWN)
        time.sleep(0.1)

# Обработчик команд
# 1. Поиск информации в тексте и вывод ее
def commandFindEmailAddresses(update: Update, context):
    logging.info(f"User {update.effective_user.username} call /find_email")

    update.message.reply_text('Введите текст для поиска почтовых адресов: ')

    return 'find_email'

def commandFindPhoneNumbers(update: Update, context):
    logging.info(f"User {update.effective_user.username} call /find_phone")

    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'find_phone_number'

# 2. Проверка сложности пароля регулярным выражением. 
def commandVerifyPassword(update: Update, context):
    logging.info(f"User {update.effective_user.username} call /verify_password")

    update.message.reply_text('Введите пароль для проверки: ')

    return 'verify_password'

def commandGetEmails(update: Update, context):
    update.message.reply_text("Сохраненные почтовые адреса:\n"+db_execute("SELECT * FROM emails;"))

def commandGetPhones(update: Update, context):
    update.message.reply_text("Сохраненные телефонные номера:\n"+db_execute("SELECT * FROM phones;"))

def commandGetReplLogs(update: Update, context):
    data = db_execute("SELECT * FROM pglog;")
    messageSendMD(update, data)

# 3. Мониторинг Linux-системы
def commandLinux(update: Update, context):
    user_input = update.message.text 

    match user_input:
        case "/get_release":
            command = "lsb_release -a"

        case "/get_uname":
            command = "uname -a"

        case "/get_uptime":
            command = "uptime"

        case "/get_df":
            command = "df -h"

        case "/get_free":
            command = "free -h"

        case "/get_mpstat":
            command = "mpstat"

        case "/get_w":
            command = "w"

        case "/get_auths":
            command = "last -n 10"

        case "/get_critical":
            command = "journalctl -p 2 -n 5"

        case "/get_ps":
            command = "ps aux"

        case "/get_ss":
            command = "ss -tuln"

        case "/get_apt_list":
            command = "apt list --installed"

        case "/get_services":
            command = "systemctl list-units --type=service --state=running"

        case _:
            return ConversationHandler.END
    
    logging.info(f"User {update.effective_user.username} call {user_input}")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    client.connect(hostname=HOST, username=USER_NAME, password=PASSWORD, port=PORT)

    stdin, stdout, stderr = client.exec_command(command)

    data = stdout.read() + stderr.read()
    client.close()

    data = str(data).replace('\\n', '\n').replace('\\t', '\t')[2:-1]

    messageSendMD(update, data)
    logging.info(f"User {update.effective_user.username}: {user_input} - reply sent")

    return ConversationHandler.END


def findEmailAddresses(update: Update, context):
    logging.debug(f"User {update.effective_user.username}: /find_email - sent text")

    user_input = update.message.text

    emailRegex = re.compile(r'\w+@[a-z]+\.[a-z]+')

    emailList = emailRegex.findall(user_input) 

    if not emailList:
        logging.info(f"User {update.effective_user.username}:/find_email got no addresses")

        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END
    
    emailAddresses = "Найденные почтовые адреса: \n"
    for i in range(len(emailList)):
        emailAddresses += f'{i+1}. {emailList[i]}\n'
        
    update.message.reply_text(emailAddresses + "\nСохранить данные в базу данных? (Да/Нет)")
    context.user_data['emailList'] = emailList

    logging.info(f"User {update.effective_user.username}:/find_email got {len(emailList)} addresses")

    return "ask_for_save_emails"

def findPhoneNumbers (update: Update, context):
    logging.debug(f"User {update.effective_user.username}: /find_phone - sent text")

    user_input = update.message.text

    phoneNumRegex = re.compile(r'(?:\+7|8)\s?[-(]?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}')

    phoneNumberList = phoneNumRegex.findall(user_input) 

    if not phoneNumberList:
        logging.info(f"User {update.effective_user.username}:/find_phone got no phones")

        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END
    
    phoneNumbers = "Найденные телефонные номера: \n"
    for i in range(len(phoneNumberList)):
        phoneNumbers += f'{i+1}. {phoneNumberList[i]}\n'
        
    update.message.reply_text(phoneNumbers + "\nСохранить данные в базу данных? (Да/Нет)")
    context.user_data['phoneNumberList'] = phoneNumberList

    logging.info(f"User {update.effective_user.username}:/find_phone got {len(phoneNumberList)} phones")

    return "ask_for_save_phones"

def verifyPassword(update: Update, context):
    logging.debug(f"User {update.effective_user.username}: /verify_password - sent password")

    user_input = update.message.text

    passwordRegex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$')

    if passwordRegex.match(user_input):
        logging.info(f"User {update.effective_user.username}:/verify_password - verified")

        update.message.reply_text("Пароль сложный")

        return ConversationHandler.END
    else:
        logging.info(f"User {update.effective_user.username}:/verify_password - not verified")

        update.message.reply_text("Пароль простой")

        return ConversationHandler.END


def saveEmailAddresses(update: Update, context):
    if update.message.text == "Да":
        
        db_command = "INSERT INTO emails (email) VALUES "
        for i in context.user_data["emailList"]:
            db_command += f"('{i}'),"
        db_command = db_command[:-1] + "RETURNING *;"
        
        if db_execute(db_command) != "error":
            update.message.reply_text("Данные сохранены")
        else:
            update.message.reply_text("Данные не сохранены из за ошибки в базе данных")

        return ConversationHandler.END
    else:
        return ConversationHandler.END
    
def savePhoneNumbers(update: Update, context):
    if update.message.text == "Да":
        
        db_command = "INSERT INTO phones (phone) VALUES "
        for i in context.user_data["phoneNumberList"]:
            db_command += f"('{i}'),"
        db_command = db_command[:-1] + "RETURNING *;"
        
        if db_execute(db_command) != "error":
            update.message.reply_text("Данные сохранены")
        else:
            update.message.reply_text("Данные не сохранены из за ошибки в базе данных")

        return ConversationHandler.END
    else:
        return ConversationHandler.END


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    logging.info("-"*10+'BOT STARTED'+'-'*10) 

    # Обработчик диалога
    convHandlerFindEmailAddresses = ConversationHandler(
        entry_points=[CommandHandler('find_email', commandFindEmailAddresses)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, findEmailAddresses)],
            'ask_for_save_emails': [MessageHandler(Filters.text & ~Filters.command, saveEmailAddresses)],
        },
        fallbacks=[]
    )
    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', commandFindPhoneNumbers)],
        states={
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            'ask_for_save_phones': [MessageHandler(Filters.text & ~Filters.command, savePhoneNumbers)],
        },
        fallbacks=[]
    )
    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verify_password', commandVerifyPassword)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verifyPassword)],
        },
        fallbacks=[]
    )

	# Регистрируем обработчики команд
    #dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("get_emails", commandGetEmails))
    dp.add_handler(CommandHandler("get_phone_numbers", commandGetPhones))
    dp.add_handler(convHandlerFindEmailAddresses)
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerVerifyPassword)

    dp.add_handler(CommandHandler("get_repl_logs", commandGetReplLogs))
    dp.add_handler(MessageHandler(Filters.command, commandLinux))

		
    updater.start_polling()

    updater.idle()
    logging.info("-"*10+'BOT STOPED'+'-'*10) 


if __name__ == '__main__':
    main()