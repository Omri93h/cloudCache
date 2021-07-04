import requests
import json

from ec2_node.nodeCache import NodeCache


class Ec2Node:
    """
    Ec2 Node class for ELB distributed cache system
    """

    def __init__(self, vpc_port):
        self._vpc_port = vpc_port
        self.ip = ""
        self.cache = NodeCache()
        self.backup_cache = NodeCache(True)
        self.secondary_node = ""

    def post_to_target_node(self, key, data, expiration_date, target_node_ip):
        """
        Sends a post request to the target node with the required info
        :param key:             For the target_node to use as the data's cache key
        :param data:            Data needed to be stored on the target_node
        :param expiration_date: Cache item's expiration date
        :param target_node_ip:  IP address of the target_node
        :return:
        """
        try:
            res = requests.post(
                f'http://{target_node_ip}:{self._vpc_port}/api/set_value?str_key={key}&data={data}&expiration_date={expiration_date}')
            # res = json.dumps({'status_code': 200, "item": res})
        except requests.exceptions.ConnectionError:
            res = json.dumps({'status_code': 404})
        return res

    def get_from_target_node(self, key, target_node_ip):
        """
        Sends a get request to the target node to receive the data of the given key that is in the target nodes cache
        :param key:
        :param target_node_ip:
        :return:
        """
        try:
            res = requests.get(
                f'http://{target_node_ip}:{self._vpc_port}/api/get_value?str_key={key}')
        except requests.exceptions.ConnectionError:
            res = json.dumps({'status_code': 404})
        return res

    def store_data_and_post_req(self, key, data, expiration_date, target_node_ip):
        """
        Stores data in this nodes cache and then posts it to its balancer target node
        :param key:
        :param data:
        :param expiration_date:
        :param target_node_ip:
        :return:
        """
        has_been_cached = self.store_data_in_cache(key, data, expiration_date)
        self.readjust_cache()
        if has_been_cached:
            res = self.post_to_target_node(key, data, expiration_date, target_node_ip)
        return res

    def get_data_and_get_req(self, key, target_node_ip):
        """
        Stores data in this nodes cache and then posts it to its balancer target node
        :param key:
        :param target_node_ip:
        :return:
        """
        data_from_cache = self.store_data_in_cache(key)
        if data_from_cache is None:
            data_from_cache = self.get_from_target_node(key, target_node_ip)
        return data_from_cache

    def store_data_in_cache(self, key, data, expiration_date):
        return self.cache.put(key, data, expiration_date)

    def store_data_in_backup(self, key, data, expiration_date):
        return self.backup_cache.put(key, data, expiration_date)

    def get_data_from_cache(self, key):
        return self.cache.get(key)

    def get_data_from_backup(self, key):
        return self.backup_cache.get(key)

    def get_full_cache(self):
        return {"cache": self.get_main_cache(),
                "back_up_cache": self.get_backup_cache()}

    def get_main_cache(self):
        return self.cache.get_full_cache()

    def get_backup_cache(self):
        return self.backup_cache.get_full_cache()

    def readjust_cache(self):
        """
        This method readjusts the cache's of THIS no so there aren't any duplicate
        key,value pairs between the main cache and the backup cache
        :return:
        """
        primary_cache = self.get_main_cache()
        backup_cache = self.get_backup_cache()
        for key_prime, val_prime in primary_cache.items():
            if key_prime in backup_cache:
                val_in_backup_cache = backup_cache.get(key_prime)
                if val_prime == val_in_backup_cache:
                    self.backup_cache.pop_item(key_prime)



