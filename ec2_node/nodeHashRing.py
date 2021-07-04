from datetime import datetime
from uhashring import HashRing


class NodeHashRing:
    """
    Our Hash ring object
    """

    def __init__(self, db_table):
        self.dynamo_table = db_table
        self.num_live_nodes = 0
        self.prev_num_live_nodes = 0
        self.live_nodes = []
        self.do_backup = False
        self.live_nodes, self.do_backup = self.get_live_node_list()
        self.change_in_num_nodes = False
        self.hash_ring = HashRing(nodes=self.live_nodes)
        self._last_updated = 0
        self.get_current_time()

    def get_live_node_list(self) -> []:
        """
        Set value in our node's cache
        :return:
        """
        do_backup = False
        try:
            response = self.dynamo_table.scan()
            now = self.get_current_time()

            new_live_nodes = [item['IP'] for item in response['Items'] if
                               int(item['lastActiveTime']) >= now - 15000]

            if abs(len(new_live_nodes)-len(self.live_nodes)) != 0:
                self.set_num_live_and_prev_nodes(len(new_live_nodes))
                do_backup = True

            self.live_nodes = new_live_nodes

        except Exception as e:
            print(f'Error in get_live_node_list: {e}')

        return self.live_nodes, do_backup

    def set_num_live_and_prev_nodes(self, new_num_nodes):
        self.prev_num_live_nodes = self.num_live_nodes
        self.num_live_nodes = new_num_nodes

    def num_difference_in_nodes(self):
        return abs(self.num_live_nodes - self.prev_num_live_nodes)

    def get_target_node(self, key):
        return self.hash_ring.get_node(key)

    def get_target_and_alt_node_ips(self, key):
        self.update_live_nodes()
        main_node = self.hash_ring.get_node(key)
        if main_node is None:
            self.update_live_nodes()
        self.hash_ring.remove_node(main_node)
        alt_node = self.hash_ring.get_node(key)

        if alt_node is None:
            alt_node = -1
        self.hash_ring.add_node(main_node)

        return main_node, alt_node

    def update_live_nodes(self):
        live_nodes_list, do_backup = self.get_live_node_list()
        nodes_to_remove = []
        for node in live_nodes_list:
            if node not in self.hash_ring.get_nodes():
                self.hash_ring.add_node(node)

        for node_key in self.hash_ring.get_nodes():
            if node_key not in live_nodes_list:
                nodes_to_remove.append(node_key)

        for node_key in nodes_to_remove:
            self.hash_ring.remove_node(node_key)

        return do_backup

    def update_hash_ring(self, current_live_nodes):
        self.set_num_live_and_prev_nodes(len(current_live_nodes))
        self.live_nodes = current_live_nodes
        self.hash_ring = HashRing(nodes=self.live_nodes)

    def get_current_time(self):
        self._last_updated = int(round(datetime.now().timestamp()) * 1000)
        return self._last_updated

    def to_string(self):
        return str(self.hash_ring.nodes)
