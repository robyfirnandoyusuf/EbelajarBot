"""bot.py: This project just for fun tho !"""

__author__      = "greycat"
__copyright__   = "Copyright 2022, Planet Mars"

import requests
import json
from datetime import datetime
from telegram import ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import prettytable as pt
import sqlite3  
import time

token = "" #ISI TOKEN BOT

conn = sqlite3.connect('database.db', check_same_thread=False)

headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
    'Connection': 'keep-alive',
    'Origin': 'https://ebelajar.stiki.ac.id',
    'Referer': 'https://ebelajar.stiki.ac.id/my/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

json_param = [
    {
        'index': 0,
        'methodname': 'core_calendar_get_action_events_by_timesort',
        'args': {
            'limitnum': 20,
            'timesortfrom': 1664730000,
        },
    },
]

def start(update, ctx):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')
    
def echo(update, ctx):
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def fetchEbelajar(username):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE tele_id = '{username}'")
    user = cur.fetchone()
    
    cookies = {
        'MoodleSession': user[4],
        '_ga': 'GA1.3.688967763.1665975201',
        '_gid': 'GA1.3.84978362.1665975201',
        '_gat_gtag_UA_99652577_2': '1',
    }

    params = {
        'sesskey': user[3],
        'info': 'core_calendar_get_action_events_by_timesort',
    }
    
    response = requests.post('https://ebelajar.stiki.ac.id/lib/ajax/service.php', params=params, cookies=cookies, headers=headers, json=json_param, verify=False)
    json_data = response.text
    data = json.loads(json_data)

    events = data[0]['data']['events']
    return events 

def display(update, ctx):
    username = update.message.chat.username
    events = fetchEbelajar(username)
    table = pt.PrettyTable(['Title', 'Code', 'Deadline', 'URL'])
    
    for v in events:
        dt_obj = datetime.fromtimestamp(v['timestart'])
        table.add_row([v['name'], v['course']['fullnamedisplay'], dt_obj, v['url']])
    update.message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)
    
def polling():
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM users")
        users = cur.fetchall()
        for user in users:
            username = user[1]

            arrEvents = []
            events = fetchEbelajar(username)
            
            cur.execute(f"SELECT * FROM tasks")
            tasks = cur.fetchall()
            
            # pluck event id and insert
            for v in events:
                event_id = str(v['id'])
                arrEvents.append(event_id)
                checkTask = cur.execute(f"SELECT * FROM tasks WHERE event_id = '{event_id}'")

                if (checkTask.fetchone() == None):
                    query = f"INSERT INTO tasks (_id,event_id,code,name,url,user_id,epoch_timeline,epoch_start,epoch_end) VALUES (null, '{v['id']}', '{v['course']['fullnamedisplay']}', '{v['name']}', '{v['url']}', '{user[0]}', '{v['timestart']}', '{v['course']['startdate']}', '{v['course']['enddate']}')"
                    cur.execute(query)
            
            arrEventsDb = []
            for t in tasks:
                arrEventsDb.append(t[2])
            
            diff = list(set(arrEvents).symmetric_difference(set(arrEventsDb)))
            print(diff)

            cur.execute(f"SELECT * FROM tasks WHERE event_id in ('{','.join(diff)}') ")
            tasks_rep = cur.fetchall()
            conn.commit()

            if (len(tasks_rep) >= 1):
                table = pt.PrettyTable(['Title', 'Code', 'Deadline', 'URL'])
                for v in tasks_rep:
                    dt_obj = datetime.fromtimestamp(int(v[6]))
                    table.add_row([v[4], v[3], dt_obj, v[5]])
                # update.message.reply_text(f'<b>NEW EVENT !!!!</b>\n<pre>{table}</pre>', parse_mode=ParseMode.HTML)
                sendMsg(user[2], f'<b>NEW EVENT !!!!</b>\n<pre>{table}</pre>')
    except BaseException as e:
        sendMsg(user[2], 'Polling failed: ' + str(e) + ' . Please contact the Handsome Admin !')

def sendMsg(chat_id, text):
    url_req = "https://api.telegram.org/bot" + token + "/sendMessage" + "?chat_id=" + chat_id + "&text=" + text+"&parse_mode=html"
    res = requests.get(url_req)
    return res

def register(update, ctx):
    username = update.message.chat.username
    chat_id = update.message.chat.id
    
    try:
        sesskey = str(update.message.text).split(' ')[1]
        cookie = str(update.message.text).split(' ')[2]
        
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM users WHERE tele_id = '{username}'")
        user = cur.fetchone()
        
        if (user == None):
            cur.execute(f"INSERT INTO users (_id,tele_id,sesskey,cookie,chat_id) VALUES (null, '{username}', '{sesskey}', '{cookie}', '{chat_id}')")
        else:
            cur.execute(f"UPDATE users SET sesskey = '{sesskey}', cookie = '{cookie}', chat_id = '{chat_id}' WHERE tele_id = '{username}'")
        
        events = fetchEbelajar(username)
        for v in events:
            cur.execute(f"INSERT INTO tasks (_id,event_id,code,name,url,user_id,epoch_timeline,epoch_start,epoch_end) VALUES (null, '{v['id']}', '{v['course']['fullnamedisplay']}', '{v['name']}', '{v['url']}', '{user[0]}', '{v['timestart']}', '{v['course']['startdate']}', '{v['course']['enddate']}')")
        conn.commit()
        
        update.message.reply_text('Register Success !')
    except BaseException as e:
        update.message.reply_text('Register failed: ' + str(e) + ' . Please contact the Handsome Admin !')
    
def main():
    """Start the bot."""
    
    print("Bot Started!")

    updater = Updater(token, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("display", display))
    dp.add_handler(CommandHandler("register", register))
    dp.add_handler(CommandHandler("polling", polling))
    dp.add_handler(CommandHandler("help", help))

    dp.add_handler(MessageHandler(Filters.text, echo))

    # Start the Bot
    updater.start_polling()
    
    while True:
        polling()
        print('polled !')
        time.sleep(3) # Sleep for 3 seconds
    updater.idle()


if __name__ == '__main__':
    main()