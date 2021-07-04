from flask import Flask, request
import json
from datetime import datetime
import requests
import boto3

from ec2_node.ec2Node import Ec2Node
from ec2_node.nodeHashRing import NodeHashRing

ec2_node = Ec2Node(8080)

dynamodb = boto3.resource('dynamodb', region_name="us-east-2")
table = dynamodb.Table('ActiveNodes')
app = Flask(__name__)
nodes_hash_ring = NodeHashRing(table)
live_nodes_pool = 1


def get_current_time():
    return int(round(datetime.now().timestamp())*1000)


@app.route('/get', methods=['GET'])
def get():
    """
    Main API entry point
    get(str_key) → null or data
    :return: null or data
    """
    nodes_hash_ring.update_live_nodes()
    key = request.args.get('str_key')
    node, alt_node = nodes_hash_ring.get_target_and_alt_node_ips(key)
    try:
        ans = ec2_node.get_data_and_get_req(key, node)
        ec2_node.secondary_node = node
    except requests.exceptions.ConnectionError:
        try:
            ans = ec2_node.get_data_and_get_req(key, alt_node)
            ec2_node.secondary_node = alt_node
        except requests.exceptions.ConnectionError:
            ans = json.dumps({'status_code': 404})
    update_health_table()

    if ans is None:
        return json.dumps({'status_code': 200,
                          'Invalid Key': f'Key, value pair for {key} doesn\"t exist in '
                                        'any cache in system'})
    return ans


@app.route('/put', methods=['GET', 'POST'])
def put():
    """
    Main API entry point
    put (str_key, data, expiration_date)
    """
    nodes_hash_ring.update_live_nodes()
    key = request.args.get('str_key')
    data = request.args.get('data')
    expiration_date = request.args.get('expiration_date')
    node, alt_node = nodes_hash_ring.get_target_and_alt_node_ips(key)
    if node == ec2_node.ip:
        nodes_hash_ring.hash_ring.remove_node(node)
        new_main = nodes_hash_ring.hash_ring.get_node(key)
        nodes_hash_ring.hash_ring.remove_node(new_main)
        new_alt_node = nodes_hash_ring.hash_ring.get_node(key)
        nodes_hash_ring.hash_ring.add_node(new_main)
        nodes_hash_ring.hash_ring.add_node(new_alt_node)
        node = new_main
        alt_node = new_alt_node

    try:
        ans = ec2_node.store_data_and_post_req(key, data, expiration_date, node)
        ec2_node.secondary_node = node
    except requests.exceptions.ConnectionError:
        try:
            ans = ec2_node.store_data_and_post_req(key, data, expiration_date, alt_node)
            ec2_node.secondary_node = alt_node
        except requests.exceptions.ConnectionError:
            ans = json.dumps({'status_code': 404})
    update_health_table()
    return ans.json()


# API calls between all of the nodes in the distributed cache system. Ideally not accessible by the user


@app.route('/api/get_val', methods=['GET'])
def get_value():
    """
    Get the value of the given key from THIS nodes backup cache of the sender node
    :return: the data value of the given key from the cache
    """
    try:
        key = request.args.get('str_key')
        item = ec2_node.get_data_from_backup(key)
        res = json.dumps({'status code': 200, 'item': item})
        update_health_table()
    except Exception as e:
        res = json.dumps(
            {'status code': 400, 'item': f"Error: {e}"})
    return res


@app.route('/api/set_value', methods=['POST'])
def set_value():
    """
    Sets a key in THIS nodes backup cache for the sender with the data value
    :return: Status code
    """
    try:
        key = request.args.get('str_key')
        data = request.args.get('data')
        expiration_date = request.args.get('expiration_date')
        store_res = ec2_node.store_data_in_backup(key, data, expiration_date)
        ec2_node.readjust_cache()
        res = json.dumps({'status code': 200, 'item': store_res})
        update_health_table()
    except Exception as e:
        res = json.dumps({'status code': 400, 'item': f"Error: {e}"})
    return res


@app.route('/api/print-cache', methods=['GET','POST'])
def show_cache():
    """
    For Testing Purposes
    :return:
    """
    try:
        data = json.dumps(
            {'status code': 200, 'item': ec2_node.get_full_cache()})
    except Exception as e:
        data = json.dumps(
            {'status code': 400, 'item': f"Error: {e}"})
    return data


@app.route('/api/show_me_the_living', methods=['GET','POST'])
def get_live_nodes():
    live_nodes_list, _ = nodes_hash_ring.get_live_node_list()
    return json.dumps(
            {'status code': 200, 'item': live_nodes_list})


def update_health_table():
    timestamp = get_current_time()
    res = table.update_item(
        Key={
            'IP': ip_address
        },
        UpdateExpression='set lastActiveTime= :val1',
        ExpressionAttributeValues={
            ':val1': timestamp,
        }
    )
    app.logger.info(f'{res}')
    return timestamp


@app.route('/health-check', methods=['GET', 'POST'])
def health_check():
    time_stamp = update_health_table()
    print(f'Here in Health Check: {ip_address} node still alive at {time_stamp}')
    node_health_check()
    return json.dumps({'status code': 200, 'timestamp': time_stamp})

@app.route('/')
def hello_world():
    print(f'Here in hello world')
    timestamp = get_current_time()
    item = {'IP': ip_address,
            'lastActiveTime': timestamp
            }
    table.put_item(Item=item)
    nodes_hash_ring.update_live_nodes()
    return 'Hello World!'


def node_health_check():
    current_live_nodes, _ = nodes_hash_ring.get_live_node_list()
    num_current_live_nodes = len(current_live_nodes)
    print(f"Here in node_health_check. Current live nodes=> {current_live_nodes}")
    if num_current_live_nodes != live_nodes_pool:
        update_hash_ring_nodes_with_data(current_live_nodes, num_current_live_nodes)


def update_hash_ring_nodes_with_data(current_live_nodes, new_num_live_nodes):
    print("Here in update_hash_ring_nodes_with_data")
    global live_nodes_pool
    nodes_hash_ring.update_hash_ring(current_live_nodes)
    node_cache = ec2_node.cache.get_full_cache().copy()
    for key in node_cache:
        new_main_node, new_alt_node = nodes_hash_ring.get_target_and_alt_node_ips(key)

        if (ec2_node.secondary_node != new_main_node) or \
            (ec2_node.secondary_node != new_alt_node):
            date_from_key = ec2_node.cache.pop_item(key)
            print(f"Printing cache data: {date_from_key}")
            data = date_from_key["data"]
            expiration_date = date_from_key["expiration_date"]
            try:
                ec2_node.store_data_and_post_req(key, data, expiration_date, new_main_node)
                ec2_node.secondary_node = new_main_node
            except requests.exceptions.ConnectionError:
                try:
                    ec2_node.store_data_and_post_req(key, data, expiration_date,
                                                     new_alt_node)
                    ec2_node.secondary_node = new_alt_node
                except requests.exceptions.ConnectionError:
                    continue

    live_nodes_pool = new_num_live_nodes


@app.before_first_request
def setup():
    global ip_address
    ip_address = requests.get('https://api.ipify.org').text
    ec2_node.ip = ip_address
    update_health_table()
    app.logger.info(f'My public IP address is: {ip_address}')


if __name__ == '__main__':
    setup()
    app.run(host='0.0.0.0', port=8080)


