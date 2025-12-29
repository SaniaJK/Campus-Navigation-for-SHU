from xml.dom.minidom import parse
import xml.dom.minidom
import bisect
import math
import sys
from time import time

def timer(func):
    def func_wrapper(*args, **kwargs):
        time_start = time()
        result = func(*args, **kwargs)
        time_end = time()
        # print(f'{func.__name__} cost {time_end - time_start}s')
        return result
    return func_wrapper

class node():
    def __init__(self, nodeid=-1, lat=-91.0, lon=-1.0):
        self.id = nodeid
        self.lat = lat
        self.lon = lon
        self.connection_nodes_type1 = []
        self.connection_nodes_type2 = []
        self.pre = None
        self.distance = sys.maxsize

    # 修复了之前会导致报错的比较逻辑
    def id_in_connection(self, cn, id):
        if not cn:
            return False
        # 关键修复: 填充元组以匹配长度
        pos = bisect.bisect_left(cn, (id, node(), 0.0, 0.0))
        if pos >= len(cn):
            return False
        if cn[pos][0] == id:
            return True
        else:
            return False

    def add_connection(self, node_id, nd, distance, azimuth, type):
        if not self.id_in_connection(self.connection_nodes_type1, node_id):
            bisect.insort(self.connection_nodes_type1,
                          (node_id, nd, distance, azimuth))
        if type == 2:
            if not self.id_in_connection(self.connection_nodes_type2, node_id):
                bisect.insort(self.connection_nodes_type2,
                              (node_id, nd, distance, azimuth))

    def __lt__(self, other):
        return self.id < other.id

class OSMParser():
    def __init__(self, datapath):
        self.nodes = []
        self.building_polygons = {} 
        print(f"Loading map data from {datapath}...")
        self.load(datapath)
        print("Map data loaded and graph built.")

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        lon_1, lat_1, lon_2, lat_2 = map(math.radians, [lon1, lat1, lon2, lat2])
        dlon = lon_2 - lon_1
        dlat = lat_2 - lat_1
        # Haversine 公式
        a = math.sin(dlat / 2) ** 2 + math.cos(lat_1) * math.cos(lat_2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371.393 * 1000 # 地球半径（米） 
        return c * r

    def calculate_azimuth(self, lat1, lon1, lat2, lon2):
        return 0.0 # 简化，暂不使用方位角

    def nodes_loc(self, nodelist, id):
        pos = bisect.bisect_left(nodelist, (id, node()))
        if pos < len(nodelist) and nodelist[pos][0] == id:
            return pos
        else:
            return None

    def nearest_node(self, nodelist, lat, lon):
        distlist = []
        for nd in nodelist:
            nd_lat, nd_lon = nd[1].lat, nd[1].lon
            distlist.append(self.calculate_distance(nd_lat, nd_lon, lat, lon))
        if not distlist: return None, None, sys.maxsize
        dist = min(distlist)
        pos = distlist.index(dist)
        out = nodelist[pos]
        return out[0], out[1], dist

    def highway_classifier(self, highway_tag):
        type2 = ['tertiary', 'residential', 'service', 'primary', 'secondary', 'unclassified']
        type1 = ['footway', 'track', 'path', 'living_street', 'pedestrian']
        if highway_tag in type2: return 2
        if highway_tag in type1: return 1
        return None

    def nodes_connection_path(self, id1, id2, highway_tag):
        nodeslist = self.nodes
        pos1 = self.nodes_loc(nodeslist, id1)
        pos2 = self.nodes_loc(nodeslist, id2)
        if pos1 is None or pos2 is None: return
        nd1, nd2 = nodeslist[pos1][1], nodeslist[pos2][1]
        tp = self.highway_classifier(highway_tag)
        if tp is None: return
        distance = self.calculate_distance(nd1.lat, nd1.lon, nd2.lat, nd2.lon)
        nd1.add_connection(id2, nd2, distance, 0, tp)
        nd2.add_connection(id1, nd1, distance, 0, tp)

    @timer
    def nodes_dropna(self):
        self.nodes_con = [x for x in self.nodes if len(x[1].connection_nodes_type1)]
        self.nodes_con_pro = [x for x in self.nodes if len(x[1].connection_nodes_type2)]

    @timer
    def load_ways(self, OSM):
        _ways = OSM.getElementsByTagName("way")
        for _way in _ways:
            flag = "None"
            highway_tag = None
            for tag in _way.getElementsByTagName("tag"):
                if tag.getAttribute("k") == "highway":
                    flag = "highway"
                    highway_tag = tag.getAttribute("v")
            # 建立连接
            if flag == "highway" and highway_tag is not None:
                pre = None
                for nd in _way.getElementsByTagName("nd"):
                    post = int(nd.getAttribute("ref"))
                    if pre is not None:
                        # 将相邻节点加入连接图
                        self.nodes_connection_path(post, pre, highway_tag)
                    pre = post

    @timer
    def load_buildings(self, OSM):
        nodelist, nodelist_con, nodelist_con_pro = self.nodes, self.nodes_con, self.nodes_con_pro
        if not nodelist_con: return
        if not nodelist_con_pro: nodelist_con_pro = nodelist_con

        self.building_name_list = []
        self.building_info_list = [] 
        self.building_polygons = {}
        processed_nodes = set() 
        _ways = OSM.getElementsByTagName("way")

        for _way in _ways:
            name = None
            for tag in _way.getElementsByTagName("tag"):
                if tag.getAttribute("k") == "name": name = tag.getAttribute("v")
            
            # 只有当它是 building 且有名字时才处理
            is_building = False
            for tag in _way.getElementsByTagName("tag"):
                if tag.getAttribute("k") in ["building", "sport", "leisure"]: is_building = True

            if is_building and name is not None:
                polygon_coords = []
                nearest_data = [None, None, sys.maxsize, None, None, sys.maxsize] # id1, node1, dist1, id2, node2, dist2

                for nd in _way.getElementsByTagName("nd"):
                    _id = int(nd.getAttribute("ref"))
                    processed_nodes.add(_id) 
                    _pos = self.nodes_loc(nodelist, _id)
                    if _pos is None: continue
                    lat, lon = nodelist[_pos][1].lat, nodelist[_pos][1].lon
                    polygon_coords.append([lat, lon])

                    # 查找接入点
                    nid1, n1, d1 = self.nearest_node(nodelist_con, lat, lon)
                    nid2, n2, d2 = self.nearest_node(nodelist_con_pro, lat, lon)
                    if d1 < nearest_data[2]: nearest_data[0:3] = [nid1, n1, d1]
                    if d2 < nearest_data[5]: nearest_data[3:6] = [nid2, n2, d2]

                if name not in self.building_name_list and nearest_data[0] is not None:
                    self.building_name_list.append(name)
                    self.building_info_list.append((name, (nearest_data[0], nearest_data[1]), (nearest_data[3], nearest_data[4])))
                    self.building_polygons[name] = polygon_coords

        _nodes = OSM.getElementsByTagName("node")
        for _node in _nodes:
             name = None
             _id = int(_node.getAttribute("id"))
             if _id in processed_nodes: continue
             for tag in _node.getElementsByTagName("tag"):
                 if tag.getAttribute("k") == "name": name = tag.getAttribute("v")
             if name is not None:
                 lat, lon = float(_node.getAttribute("lat")), float(_node.getAttribute("lon"))
                 if not self.check_bounds((lat, lon)): continue
                 nid1, n1, _ = self.nearest_node(nodelist_con, lat, lon)
                 nid2, n2, _ = self.nearest_node(nodelist_con_pro, lat, lon)
                 if name not in self.building_name_list:
                     self.building_name_list.append(name)
                     self.building_info_list.append((name, (nid1, n1), (nid2, n2)))
                     self.building_polygons[name] = []

    @timer
    def load_nodes(self, OSM):
        _nodes = OSM.getElementsByTagName("node")
        for _node in _nodes:
            node_id = int(_node.getAttribute("id"))
            lat = float(_node.getAttribute("lat"))
            lon = float(_node.getAttribute("lon"))
            bisect.insort(self.nodes, (node_id, node(node_id, lat, lon)))

    def load_bounds(self, OSM):
        _bounds = OSM.getElementsByTagName("bounds")
        if _bounds:
            bound = _bounds[0]
            self.minlat, self.maxlat = float(bound.getAttribute("minlat")), float(bound.getAttribute("maxlat"))
            self.minlon, self.maxlon = float(bound.getAttribute("minlon")), float(bound.getAttribute("maxlon"))
        else:
            self.minlat, self.maxlat, self.minlon, self.maxlon = 31.30, 31.33, 121.38, 121.40

    def check_bounds(self, pos):
        return (self.minlat <= pos[0] <= self.maxlat) and (self.minlon <= pos[1] <= self.maxlon)

    @timer
    def load(self, datapath):
        DOMTree = xml.dom.minidom.parse(datapath)
        OSM = DOMTree.documentElement
        self.load_bounds(OSM)
        self.load_nodes(OSM)
        self.load_ways(OSM)
        self.nodes_dropna()
        self.load_buildings(OSM)

    @timer
    def Shortest_path_node(self, start_node_tuple, end_node_tuple, type):
        def node_clear(nl):
            for nt in nl:
                nt[1].pre = None; nt[1].distance = sys.maxsize
        
        start_node, end_node = start_node_tuple[1], end_node_tuple[1]
        nodelist = self.nodes_con.copy() if type == 1 else self.nodes_con_pro.copy()
        
        # 简单检查起点是否在列表
        found_start = False
        for item in nodelist:
            if item[0] == start_node_tuple[0]: found_start = True; break
        if not found_start: return [], sys.maxsize
            
        node_clear(nodelist)
        start_node.distance = 0
        queue = nodelist.copy()
        
        while queue:
            node_proc_tuple = min(queue, key=lambda x: x[1].distance)
            node_proc = node_proc_tuple[1]
            queue.remove(node_proc_tuple)
            if node_proc.distance == sys.maxsize: break
            if node_proc == end_node: break
            
            connections = node_proc.connection_nodes_type1 if type == 1 else node_proc.connection_nodes_type2
            for nd_next_tuple in connections:
                nd_next_node, nd_next_dist = nd_next_tuple[1], nd_next_tuple[2]
                alt = nd_next_dist + node_proc.distance
                if alt < nd_next_node.distance:
                    nd_next_node.distance = alt
                    nd_next_node.pre = node_proc

        if end_node.distance == sys.maxsize: return [], sys.maxsize
        route = []
        nd = end_node
        while nd:
            route.append(nd)
            nd = nd.pre
        route.reverse()
        return route, end_node.distance

    @timer
    def Shortest_path_pos(self, start_pos, end_pos, type):
        if not (self.check_bounds(start_pos) and self.check_bounds(end_pos)): return [], -1
        
        src_list = self.nodes_con if type == 1 else self.nodes_con_pro
        sid, snode, sdist = self.nearest_node(src_list, start_pos[0], start_pos[1])
        eid, enode, edist = self.nearest_node(src_list, end_pos[0], end_pos[1])

        if not snode or not enode: return [], -1
        if sid == eid: return [start_pos, (snode.lat, snode.lon), end_pos], sdist + edist

        route, dist = self.Shortest_path_node((sid, snode), (eid, enode), type)
        if dist == sys.maxsize: return [], -1

        path = [start_pos] + [(nd.lat, nd.lon) for nd in route] + [end_pos]
        return path, dist + sdist + edist