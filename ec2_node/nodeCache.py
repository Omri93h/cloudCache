from datetime import datetime
import sys


class NodeCache:
    """
    Our EC2 nodes cache class object. This will hold all of our node's relevant data and allow us to easily
    execute operations on it
    """
    def __init__(self, is_backup=False):
        self._cache = dict()
        self._is_backup = is_backup
        self._last_updated = 0
        self.has_been_backed_up = False
        self.update_time()

    def put(self, key, data, expiration_date):
        """
        Set value in our node's cache
        :param key:
        :param data: data value
        :param expiration_date: expiration value of this cache data item (Not of the cache itself)
        :return:
        """
        try:
            self._cache[key] = {
                "data": data,
                "expiration_date": expiration_date
            }
            self.update_time()
            return True
        except Exception as e:
            sys.stdout.write(f"Error setting value in cache: {e}")
            return False

    def get(self, key):
        """
        Get value from cache given key
        :param key:
        :return: the value of the key from the nodes cache
        """
        data = None
        try:
            data = self._cache[key]["data"]
            self.update_time()
        except Exception as e:
            sys.stdout.write(f"Error in getting value from cache: {e}")

        return data

    def get_full_cache(self):
        """
        Returning the full cache of our node
        :return:
        """
        self.update_time()
        return self._cache

    def pop_item(self, key):
        return self._cache.pop(key)

    def update_time(self):
        self._last_updated = round(datetime.now().timestamp())
