import socket
import time
import json
import os
from ping3 import ping
import chardet
import re
import subprocess
import threading
import requests
import ipaddress
import numpy as np

iteration = 10


def check_file_encoding(file_path):

    with open(file_path, 'rb') as file:
        result = chardet.detect(file.read())

    encoding = result['encoding']
    return encoding


"""
def balance_data(domian):
    n_of_ipv4 = len(domian["ipv4"])
    n_of_ipv6 = len(domian["ipv6"])
    if n_of_ipv6 > n_of_ipv4:
        domian["ipv6"] = domian["ipv6"][0:n_of_ipv4]
    return domian
"""

def is_valid_ipv6(address):
    try:
        ip = ipaddress.IPv6Address(address)
        return True
    except ipaddress.AddressValueError:
        return False


def is_valid_ipv4(address):
    try:
        ip = ipaddress.IPv4Address(address)
        return True
    except ipaddress.AddressValueError:
        return False

# from domain-ips file to a json file
def initial_data(ip_folder_path, data_json_file_path):

    IP_ONLY_IPV4 = []
    All_IP = []
    ip_type = ""

    for filename in os.listdir(ip_folder_path):
        if ".DS" in filename:
            continue
        data = {
            "domain": "",
            "min_delay_ms_socket": {
                "ipv4": 0,
                "ipv6": 0
            },
            "avg_delay_ms_socket": {
                "ipv4": 0,
                "ipv6": 0
            },
            "stddev_delay_ms_socket": {
                "ipv4": 0,
                "ipv6": 0
            },
            # "min_delay_ms_ping": {
                # "ipv4": 0,
                # "ipv6": 0
            # },
            "ipv4": [],
            "ipv6": []
        }
        data["domain"] = filename

        file_path = os.path.join(ip_folder_path, filename)
        encoding = check_file_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            ip_addresses = f.read().splitlines()

        for ip in ip_addresses:

            ip_entry = {
                "address":"",
                "delay_ms_socket": 0,
                # "delay_ms_ping": 0,
                "min":0,
                "avg":0,
                "stddev":0
            }
            ip_entry["address"] = ip

            if is_valid_ipv4(ip):
                data["ipv4"].append(ip_entry)
            elif is_valid_ipv6(ip):
                data["ipv6"].append(ip_entry)
            else:
                print("ip not valid: " + ip)
                print("current: " + filename)
                continue

        #data = balance_data(data)
        
        if len(data["ipv6"]) == 0:
            # this domain does not support ipv6.
            # no need to get the delays.
            IP_ONLY_IPV4 .append(data)
            continue

        All_IP.append(data)

    with open(data_json_file_path, 'w') as f:
        json.dump(All_IP, f, indent=4)

    with open(data_json_file_path[:-5] + "_only_ipv4.json", 'w') as f:
        json.dump(IP_ONLY_IPV4, f, indent=4)


# nonono 这样接收到的不对
def delay_by_socket_test(ip):

    http_request = "GET / HTTP/1.1\r\nHost: " + ip + "\r\n\r\n"
    if "." in ip:
        # ipv4 address
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    elif ":" in ip:
        # ipv6 address
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

    # imporve effiency
    s.settimeout(10)
    try:
        s.connect((ip, 80))
    except:
        print("Error: Could not connect to URI given: " + ip)
        return None


    delays = []
    for i in range(iteration):
        try:
            start_time = time.time()
            s.send(http_request.encode())
            resp = s.recv(4096).decode()
            end_time = time.time()
        except:
            print("Error: Could not to send request or receivem msg")
        
        delay = (end_time - start_time) * 1000
        # print(delay)
        delays.append(round(delay, 3))
    
    s.close()
    return delays



# basicly check each ip
def delay_by_socket(ip):

    http_request = "GET / HTTP/1.1\r\nHost: " + ip + "\r\n\r\n"
    if "." in ip:
        # ipv4 address
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    elif ":" in ip:
        # ipv6 address
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

    # imporve effiency
    s.settimeout(5)
    try:
        s.connect((ip, 80))
    except:
        # print("Error: Could not connect to URI given: " + ip)
        return None

    try:
        start_time = time.time()
        s.send(http_request.encode())
    except:
        # print("Error: Could not send request to host: " + ip)
        return None

    try:
        resp = s.recv(4096).decode()
        end_time = time.time()
    except:
        # print("Error: Could not receive message from host: " + ip)
        return None

    s.close()

    delay = (end_time - start_time) * 1000
    return round(delay, 3)


# basicly check each ip
def delay_by_ping(ip):

    if "." in ip:
        cmd = f"ping -c {iteration} {ip} | tail -1 | awk -F/ '{{print $4}}' | awk -F'=' '{{print $2}}'"
    elif ":" in ip:
        cmd = f"ping6 -c {iteration} {ip} | tail -1 | awk -F/ '{{print $4}}' | awk -F'=' '{{print $2}}'"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output, error = process.communicate()

    if not error:
        try: 
            delay = float(output)
            return delay
        except:
            # print("Error in the ping result, the ip is: " + ip)
            return None
    
    else:
        # print("Error running the command:", error)
        return None

    # delay = ping(ip, iteration) * 1000
    # print("pingpython result: ", delay)


def get_socket_delay(ips):
    for ip_entry in ips:

        ip = ip_entry["address"]
        delays = [delay_by_socket(ip) for _ in range(iteration)]
        # print("current ip is: " + ip)
        # print(delays)
        count_of_none = delays.count(None)
        if delays == None or count_of_none > iteration/2:
            ip_entry["delay_ms_socket"] = None
            # print("result: ", delays)
            # print("ip connection not steady: " + ip)
            continue

        non_none_elements = [x for x in delays if x is not None]

        if len(non_none_elements) != iteration:
            print("exist none:", non_none_elements)

        # min_delay = min(non_none_elements)
        
        ip_entry["delay_ms_socket"] = non_none_elements
        ip_entry["min"] = np.min(non_none_elements)
        ip_entry["avg"] = round(np.mean(non_none_elements), 3)
        ip_entry["stddev"] = round(np.std(non_none_elements), 3)


def get_ping_delay(ips):
    for ip_entry in ips:
        ip = ip_entry["address"]
        # the function returns the min
        delay = delay_by_ping(ip)
        ip_entry["delay_ms_ping"] = delay


def get_delays_thread(ips):
    get_socket_delay(ips)
    # get_ping_delay(ips)


def get_delays(data_json_file_path):
    with open(data_json_file_path, 'r') as f:
        data = json.load(f)
    
    threads = []
    for item in data:
        thread_ipv4 = threading.Thread(target=get_delays_thread, args=(item["ipv4"],))
        thread_ipv6 = threading.Thread(target=get_delays_thread, args=(item["ipv6"],))

        threads.append(thread_ipv4)
        threads.append(thread_ipv6)
    
    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    with open(data_json_file_path, 'w') as f:
        json.dump(data, f, indent=4)




def compute_avg(all_ip, sub):

    length = len(all_ip)
    avg_delay = 0
    for ip in all_ip:
        avg_delay += float(ip[sub])
    if length == 0:
        return 0
    return round(avg_delay/length, 3)
def compute_avg_delay(FILEPATH):

    with open(FILEPATH, 'r') as f:
         data = json.load(f)

    # print("# of domians: " + str(len(data)))

    for domain in data:
        # print("\ncurrent domain: " + domain["domain"])
        

        avg_delay = compute_avg(domain["ipv4"], "delay_ms_socket")
        domain["avg_delay_ms_socket"]["ipv4"] = avg_delay

        avg_delay = compute_avg(domain["ipv6"], "delay_ms_socket")
        domain["avg_delay_ms_socket"]["ipv6"] = avg_delay

        avg_delay = compute_avg(domain["ipv4"], "delay_ms_ping")
        domain["avg_delay_ms_ping"]["ipv4"] = avg_delay

        avg_delay = compute_avg(domain["ipv6"], "delay_ms_ping")
        domain["avg_delay_ms_ping"]["ipv6"] = avg_delay


        # print("# of ipv4 addresses:" + str(len(domain["ipv4"])))
        # print("# of ipv6 addresses:" + str((domain["ipv6"])))

    with open(FILEPATH, 'w') as f:
        json.dump(data, f, indent=4)    


def find_min_tool(all_ip, sub):

    # find_ip = "NULL"
    min_delay = 9999.999
    min_avg = 9999.999
    min_stddev = 9999.999
    for ip in all_ip:
        if ip[sub] == None:
            continue
        # print(ip)
        # print(ip[sub])
        # tmp = ip[sub] 
        # tmp = min([x for x in ip[sub] if x is not None])

        if ip["min"]  < min_delay:
            min_delay = ip["min"] 
            # find_ip = ip["address"]
        if ip["avg"]  < min_avg:
            min_avg = ip["min"] 
            # find_ip = ip["address"]
        if ip["stddev"]  < min_stddev:
            min_stddev = ip["min"] 
            # find_ip = ip["address"]

    return min_delay, min_avg, min_stddev


def get_the_min(FILEPATH):

    with open(FILEPATH, 'r') as f:
         data = json.load(f)

    for domain in data:
        # min_delay, avg_delay, stddev_dealy = find_min_tool(domain["ipv4"], "delay_ms_socket")
        domain["min_delay_ms_socket"]["ipv4"], \
        domain["avg_delay_ms_socket"]["ipv4"], \
        domain["stddev_delay_ms_socket"]["ipv4"] \
        = find_min_tool(domain["ipv4"], "delay_ms_socket")
        # domain["min_delay_ms_socket"]["ipv4"] = str(min_delay)+"-"+ip

        domain["min_delay_ms_socket"]["ipv6"], \
        domain["avg_delay_ms_socket"]["ipv6"], \
        domain["stddev_delay_ms_socket"]["ipv6"] \
        = find_min_tool(domain["ipv6"], "delay_ms_socket")
        # domain["min_delay_ms_socket"]["ipv6"] = str(min_delay)+"-"+ip


        # min_delay, ip = find_min_tool(domain["ipv4"], "delay_ms_ping")
        # domain["min_delay_ms_ping"]["ipv4"] = str(min_delay)+"-"+ip

        # min_delay, ip = find_min_tool(domain["ipv6"], "delay_ms_ping")
        # domain["min_delay_ms_ping"]["ipv6"] = str(min_delay)+"-"+ip

    with open(FILEPATH, 'w') as f:
        json.dump(data, f, indent=4)




def main():
    ip_folder_path = "./domain_ip"
    data_json_file_path = "./domain_ip.json"


    initial_data(ip_folder_path, data_json_file_path)

    get_delays(data_json_file_path)

    get_the_min(data_json_file_path)



'''
latency by request:

start_time = time.time()
response = requests.get(url)
end_time = time.time()
'''
def calculate_statistics(data):

    minimum_value = min(data)
    
    average_value = np.mean(data)
    
    variance = np.std(data)
    
    return minimum_value, average_value, variance


if __name__ == "__main__":

    main()

    # ip = "20.236.44.162"
    # ipv6 = "2620:1ec:a92::156"


    # delays = [delay_by_socket (ip) for _ in range(iteration)]
    # print(delays)
    # print(calculate_statistics(delays))
    # latency_ms = delay_by_socket(ipv6)
    # print(delay_by_socket(ipv6),delay_by_socket(ipv6),delay_by_socket(ipv6),delay_by_socket(ipv6),delay_by_socket(ipv6))

    # latency_ms = delay_by_ping(ip)
    # print(latency_ms)
    # latency_ms = delay_by_ping(ipv6)
    # print(latency_ms)





