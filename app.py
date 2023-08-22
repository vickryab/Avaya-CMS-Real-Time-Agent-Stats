# This app used for getting the real time stats agent from CMS Supervisor without using any licensce
# Please configure host, username, password, port and also skill number (only 1 skill allowed / run)
# Big thanks to this article for a super great idea : https://www.tek-tips.com/viewthread.cfm?qid=397058 , i just make it more simple 
# Coded by @vickryab

import re
import telnetlib
import time
import json
import threading
import pytz
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

data = []
data_lock = threading.Lock()

def getdata():
    global data
    # host of avaya cms server
    host = "127.0.0.1"
    # port of avaya cms server
    port = 23
    # username of avaya cms server
    user = "cms"
    # password of avaya cms server
    password = "cms"
    dataarray = []
    tn = telnetlib.Telnet()
    tn.open(host, port)
    tn.read_until(b"login: ")
    tn.write(user.encode('utf-8') + b"\n")
    tn.read_until(b"Password: ")
    tn.write(password.encode('utf-8') + b"\n")
    islogin = tn.read_until(b"later", 5).decode('ascii')
    if "$" in islogin:
        print('[+] Connected into telnet server')
        #the clint's folder
        tn.write(b"cd /cms/toolsbin\n")
        while(True):
            tn.write(b"./clint\n")
            time.sleep(1)
            #rep:rea:spl:skill means "Report:Real Time:Split/Skill:Skill Status"
            tn.write(b'do menu 0 "rep:rea:spl:skill st"\n')
            # field 10 is the split number / 1 Means skill number
            tn.write(b'set field 10 "1"\n')
            # field 20 is refresh interval / in this case 3 seconds
            tn.write(b'set field 20 "3"\n')
            tn.write(b'do "Run"\n')
            #time.sleep(1)
            tn.write(b'logout\n')
            #time.sleep(2)
            result = tn.read_until(b"later", 5).decode('ascii')
            #result = tn.read_some().decode('ascii')
            #print(result)
            if "+Exit" in result:
                dataarray.clear() 
                # Regular expression pattern to match the desired lines
                pattern = re.compile(r'\|([a-zA-Z]+\s[a-zA-Z]+(?:\s[a-zA-Z]+)?)\s+(\d{4})\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?(?:\/[a-zA-Z]+)?)\s+((?:\d)?\/(?:\s\d)?)\s+\:(\d{2}:\d{2})')
                # Find and print the desired information
                matches = pattern.findall(result)
                for match in matches:
                    name, loginid, state, level, times = match
                    entry = {
                        "Name": name,
                        "LoginID": loginid,
                        "State": state,
                        "Skill/Level": level,
                        "Time": times
                    }
                    dataarray.append(entry)
                with data_lock:  # Acquire the lock before updating the data
                    data.clear()  # Clear the data list before updating it
                    data.extend(dataarray)
                #optional
                dt_us_central = datetime.now(pytz.timezone('Asia/Jakarta'))
                print("[", dt_us_central.strftime("%Y:%m:%d %H:%M:%S"), "] Success grabbing data...")
            
# Handler for HTTP server
class MyRequestHandler(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        if self.path == '/':
            self._set_response()
            json_data = json.dumps(data, indent=4)
            self.wfile.write(json_data.encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'404 Not Found')

# Change The port if port 8000 already used
def run(server_class=HTTPServer, handler_class=MyRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'[+] Starting server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    
    thread1 = threading.Thread(target=getdata)
    thread2 = threading.Thread(target=run)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

