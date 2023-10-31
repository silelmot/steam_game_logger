#!/usr/bin/env python3

import subprocess
import time
import re
import mysql.connector
import socket
import configparser
import os
import threading
import signal
import sys



#version
version="1.0"


STEAM_PATH = 'steam'
print(f"Version: {version}")
script_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(script_dir, "config.txt")


LOG_PATH = os.path.join(script_dir, "steam_log.txt")

def write_log(message):
    try:
      print(message)
      with open(LOG_PATH, 'a') as log_file:
          log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception as e:
       print(f"Error in write_log: {e}")
    	
    	
def execute_sql_query(db_config, query, params):
    try:
        cnx = mysql.connector.connect(**db_config)
        cursor = cnx.cursor()
        cursor.execute(query, params)
        cnx.commit()
        cursor.close()
        cnx.close()
        return True
    except Exception as e:
        write_log(f"SQL Error: {e}")
        return False
        
        
def read_config(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    
    db_config = {
        "user": config["Database"]["user"],
        "password": config["Database"]["password"],
        "host": config["Database"]["host"],
        "database": config["Database"]["database"]
    }
    
    steamapps_paths = config["SteamApps"]["paths"].split(';')
    
    login_config = {
        "enable": config.getboolean("Login", "enable", fallback=False),			#config for automatic login , if not set then false
        "numbers": config.getboolean("Login", "numbers", fallback=False),
        "user": config.get("Login", "user", fallback="default"),
        "password": config.get("Login", "password", fallback="password")
        }
    try:
    	login_config["position"] = int(config.get("Login", "position"))
    except (ValueError, configparser.NoOptionError):
    	login_config["position"] = 0
    
    return db_config, steamapps_paths, login_config


def delete_all_null(db_config, user_id, game_id):
    query = "DELETE FROM GameSessions WHERE user_id = %s AND game_id = %s AND duration IS NULL"
    params = (user_id, game_id)
    execute_sql_query(db_config, query, params)
    write_log("Spieldaten gelöscht.")

def get_current_session_id(db_config, user_id, game_id):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    cursor.execute("SELECT session_id FROM GameSessions WHERE user_id = %s AND game_id = %s AND duration IS NULL", (user_id, game_id))
    session_id = cursor.fetchone()
    cursor.close()
    cnx.close()
    
    if session_id:
        return session_id[0]
    else:
        return None

def get_or_create_user_id(db_config, pc_name):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    cursor.execute("SELECT user_id FROM Users WHERE name = %s", (pc_name,))
    user_id = cursor.fetchone()
    
    if user_id:
        cursor.close()
        cnx.close()
        return user_id[0]
    else:
        cursor.execute("INSERT INTO Users (name) VALUES (%s)", (pc_name,))
        user_id = cursor.lastrowid
        cnx.commit()
        cursor.close()
        cnx.close()
        return user_id

def get_game_id_by_app_id(db_config, app_id):
    cnx = mysql.connector.connect(**db_config)
    cursor = cnx.cursor()
    cursor.execute("SELECT game_id FROM Games WHERE app_id = %s", (app_id,))
    game_id = cursor.fetchone()
    cursor.close()
    cnx.close()
    
    if game_id:
        return game_id[0]
    else:
        return None
        
def monitor_reaper_pid(reaper_pid, db_config,game_id,user_id):
    if not reaper_pid:
        return
    while True:
        try:
            os.kill(reaper_pid, 0)  # process still working? if not, exit
        except OSError:
            return

        query = "UPDATE GameSessions SET end_time = NOW(), duration = TIMESTAMPDIFF(SECOND, start_time, NOW()) WHERE game_id = %s AND user_id = %s AND TIMESTAMPDIFF(SECOND, start_time, NOW()) > 0"
        params = (game_id, user_id)
        execute_sql_query(db_config, query, params)# if process is there, update database
.

        time.sleep(60)
        
        
def get_reaper_pid():
    pid_str = subprocess.Popen(['pgrep', '-x', 'reaper'], stdout=subprocess.PIPE).communicate()[0].decode('utf-8').strip()
    return int(pid_str) if pid_str else None


def monitor_steam():
    write_log(f"Version of this Script:{version}")
    write_log("Monitoring Steam...")
    current_app_id = None  
    steam_process = None

       
    db_config, _ , login_config= read_config(CONFIG_PATH)  
    if login_config["enable"]:	#is there a automatic login with password given in the config? ATTENTION: this can be read with systemonitor-tools as ps aux , have to be disabled for user
        if login_config["numbers"]:  # if login is numerical , number give from the pcname... in my example 6 pcs are named "jhr2 , jhr3, jhr4 and so on", number is part of password
            print("enabled and numbers")
            pc_name = socket.gethostname() 
            login_name = (login_config["user"]+ pc_name[(login_config["position"]-1):]) #get the number form the pc-name, position is set in config.txt, to add to same numberic username, my example "jugendhaus2"
            pw = (login_config["password"]+pc_name[(login_config["position"]-1):])
        else:
            print("just enabled")
            login_name = login_config["user"]
            pw = login_config["password"]
        STEAM_PATH = ['steam','-login',login_name,pw]
        print(STEAM_PATH)
    else:
        print("not even enabled")
        STEAM_PATH = ['steam']
		    	   	
    reaper_threads = set()

    while True:
        write_log("Starting Steam...")
        with subprocess.Popen(STEAM_PATH, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True) as steam_process:
            for line in steam_process.stdout:
                write_log(f"Steam output: {line.strip()}")  # Debugging: Log all

                if "Could not open connection to X" in line:
                   sys.exit("Error: Could not open connection to X detected. Exiting script.")

                if "Shutdown" in line:
                    write_log("Steam wurde beendet. Warte auf Steam-Neustart...")
                    break 

                if "SteamLaunch AppId=" in line:
                    current_app_id = re.search(r"AppId=(\d+)", line).group(1)
                    write_log(f"Game with AppId {current_app_id} started")

                    user_id = get_or_create_user_id(db_config, pc_name)
                    #print(f"UserId: {user_id}")
                    game_id = get_game_id_by_app_id(db_config, current_app_id)
                    #print(f"GameId:{game_id}")
                    if game_id:
                        delete_all_null(db_config, user_id, game_id)
                        query = "INSERT INTO GameSessions (user_id, game_id, start_time) VALUES (%s, %s, NOW())"
                        params = (user_id, game_id)
                        execute_sql_query(db_config, query, params)
                        write_log(f"Game with AppId {current_app_id} added to Table.")
                    else:
                        write_log(f"Game with AppId {current_app_id} does not exist in Games table. Skipping insertion.")
                    for rt in reaper_threads:
                        rt.join(0.1)  # short wait for threat to end properly
                    reaper_threads.clear()
         
                    reaper_pid = get_reaper_pid() 
                    write_log(f"Monitoring Reaper with PID: {reaper_pid}")
                    reaper_thread = threading.Thread(target=monitor_reaper_pid, args=(reaper_pid, db_config, game_id, user_id))
                    reaper_thread.start()
                    reaper_threads.add(reaper_thread)


                if "Uploaded AppInterfaceStats to Steam" in line and current_app_id:
                   write_log(f"Game with AppId {current_app_id} ended")
                   game_id = get_game_id_by_app_id(db_config, current_app_id)

                   session_id = get_current_session_id(db_config, user_id, game_id)
                   if session_id:

                       query = "UPDATE GameSessions SET end_time = NOW(), duration = TIMESTAMPDIFF(SECOND, start_time, NOW()) WHERE session_id = %s"
                       params = (session_id,)
                       execute_sql_query(db_config, query, params)
                       write_log(f"GameEnd with AppId {current_app_id} added to Table.")
                   else:
                       write_log(f"No Sessionid for {current_app_id}.")
                   current_app_id = None  # AppId back to default after game ended

def kill_steam_and_children():
    try:
        # Prozess-ID from steam
        steam_pid = subprocess.check_output(['pgrep', '-x', 'steam']).decode().strip()
        print(f"steampid:{steam_pid}")
        # kill Steam and all subprocesses

        subprocess.run(['pkill', '-g', steam_pid])
    except subprocess.CalledProcessError:
        print(f"steampid error")

        pass
        
def is_game_allowed(db_config, user_id, game_id):
    # Get age-restriction of user from database
    user_query = "SELECT age_restriction FROM Users WHERE user_id = %s"
    user_restriction = execute_sql_query(db_config, user_query, (user_id,))
    write_log(f"User with ID {user_id} has restriction: {user_restriction}")
    
    # get age restriction of game
    game_query = "SELECT restriction_level FROM Games WHERE game_id = %s"
    game_restriction = execute_sql_query(db_config, game_query, (game_id,))
    write_log(f"Game with ID {game_id} has restriction: {game_restriction}")
    
    if user_restriction == "18+":
        write_log(f"User with ID {user_id} is allowed to play all games.")
        return True
    elif user_restriction == "16+" and game_restriction in ["NONE", "16+"]:
        write_log(f"User with ID {user_id} is allowed to play game with ID {game_id}.")
        return True
    elif user_restriction == "NONE" and game_restriction == "NONE":
        write_log(f"User with ID {user_id} is allowed to play only games without restrictions.")
        return True
    else:
        write_log(f"User with ID {user_id} is NOT allowed to play game with ID {game_id}.")
        return False     
          
monitor_steam()
