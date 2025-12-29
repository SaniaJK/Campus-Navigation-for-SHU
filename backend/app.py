from flask import Flask, jsonify, request
from flask_cors import CORS
from parser import OSMParser
import time
import os
import sys
from datetime import datetime

app = Flask(__name__)
CORS(app)

print("Starting Flask server...")
osm_file_path = os.path.join(os.path.dirname(__file__), 'map_test.osm')
if not os.path.exists(osm_file_path):
    print(f"CRITICAL: {osm_file_path} not found")
    G_PARSER = None
else:
    G_PARSER = OSMParser(osm_file_path)

# --- 1. 时间与路况配置 ---
# 上课时间表 (开始时间)
CLASS_START_TIMES = ["08:00", "10:00", "13:00", "15:00", "18:00", "20:00"]
# 拥堵定义: 上课前 20 分钟 (例如 7:40-8:00)
CONGESTION_DURATION_MIN = 20 

# 速度配置 (m/s)
SPEED_WALK = 1.2    # 约 4.3 km/h
SPEED_BIKE = 3.1    
CONGESTION_FACTOR = 1.25 # 拥堵时骑行时间增加倍率 (变为原来的1.25倍)

def analyze_traffic(time_str):
    """
    输入: HH:MM 字符串
    输出: 骑行时间倍率 (1.0 = 正常, >1.0 = 拥堵)
    """
    try:
        current = datetime.strptime(time_str, "%H:%M")
        current_mins = current.hour * 60 + current.minute
        
        for start_str in CLASS_START_TIMES:
            cls = datetime.strptime(start_str, "%H:%M")
            cls_mins = cls.hour * 60 + cls.minute
            
            # 检查是否在 [上课前20分, 上课时间] 区间
            if (cls_mins - CONGESTION_DURATION_MIN) <= current_mins < cls_mins:
                return CONGESTION_FACTOR
                
        return 1.0 # 无拥堵
    except:
        return 1.0

# --- API ---

@app.route('/api/locations')
def get_locations():
    if not G_PARSER: return jsonify({"error": "Init fail"}), 500
    locs = []
    for b in G_PARSER.building_info_list:
        name, wn, bn = b[0], b[1][1], b[2][1]
        # 只要有步行或骑行接入点即可
        node = wn if wn else bn
        if node:
            locs.append({
                'name': name, 'lat': node.lat, 'lon': node.lon,
                'polygon': G_PARSER.building_polygons.get(name, [])
            })
    return jsonify(sorted(locs, key=lambda x: x['name']))

@app.route('/api/find_path')
def find_path():
    """ 标准导航: 同时计算步行和骑行，并根据时间推荐 """
    if not G_PARSER: return jsonify({"error": "Init fail"}), 500
    try:
        slat, slon = float(request.args.get('start_lat')), float(request.args.get('start_lon'))
        elat, elon = float(request.args.get('end_lat')), float(request.args.get('end_lon'))
        dept_time = request.args.get('time', '08:00') # HH:MM
    except: return jsonify({"error": "Params error"}), 400

    # 1. 计算拥堵系数
    bike_multiplier = analyze_traffic(dept_time)
    
    # 2. 计算步行数据
    w_path, w_dist = G_PARSER.Shortest_path_pos((slat, slon), (elat, elon), 1)
    w_time = (w_dist / SPEED_WALK) if w_dist != -1 else -1
    
    # 3. 计算骑行数据
    b_path, b_dist = G_PARSER.Shortest_path_pos((slat, slon), (elat, elon), 2)
    b_time = (b_dist / SPEED_BIKE * bike_multiplier) if b_dist != -1 else -1

    # 4. 推荐逻辑
    rec_mode = 'walk'
    if b_time != -1 and w_time != -1:
        # 如果骑行时间明显短于步行，推荐骑行；否则(拥堵严重)推荐步行
        if b_time < w_time: rec_mode = 'bike'
    elif b_time != -1: rec_mode = 'bike'
    
    return jsonify({
        "traffic_multiplier": bike_multiplier,
        "recommendation": rec_mode,
        "walk": {
            "path": w_path, "dist": w_dist, "time": w_time
        },
        "bike": {
            "path": b_path, "dist": b_dist, "time": b_time
        }
    })

@app.route('/api/find_tour')
def find_tour():
    """ 多点漫游: 返回路径及地点访问顺序 """
    if not G_PARSER: return jsonify({"error": "Init fail"}), 500
    try:
        slat, slon = float(request.args.get('start_lat')), float(request.args.get('start_lon'))
        mode = request.args.get('mode') # walk/bike
        stops_str = request.args.get('stops') # "lat,lon|lat,lon"
        # 接收 names 参数以便返回顺序
        names_str = request.args.get('names') # "Name1|Name2"
        dept_time = request.args.get('time', '08:00')
    except: return jsonify({"error": "Params error"}), 400

    # 解析途经点
    stops = []
    names = names_str.split('|') if names_str else []
    raw_stops = stops_str.split('|')
    
    for i, pair in enumerate(raw_stops):
        lat, lon = map(float, pair.split(','))
        name = names[i] if i < len(names) else "未知地点"
        stops.append({'lat': lat, 'lon': lon, 'name': name})

    # 准备计算参数
    path_type = 1 if mode == 'walk' else 2
    speed = SPEED_WALK if mode == 'walk' else SPEED_BIKE
    multiplier = 1.0
    if mode == 'bike': multiplier = analyze_traffic(dept_time)
    
    # 贪婪算法
    curr_pos = (slat, slon)
    unvisited = stops.copy()
    
    full_path = []
    total_dist = 0
    visit_sequence = ["起点"] # 记录名称顺序

    while unvisited:
        # 找最近
        nearest_idx = -1
        min_d = sys.maxsize
        for i, st in enumerate(unvisited):
            d = G_PARSER.calculate_distance(curr_pos[0], curr_pos[1], st['lat'], st['lon'])
            if d < min_d: min_d = d; nearest_idx = i
        
        target = unvisited.pop(nearest_idx)
        visit_sequence.append(target['name'])
        
        # 寻路
        seg_path, seg_dist = G_PARSER.Shortest_path_pos(curr_pos, (target['lat'], target['lon']), path_type)
        
        if seg_dist != -1:
            if full_path: full_path.extend(seg_path[1:])
            else: full_path.extend(seg_path)
            total_dist += seg_dist
        
        curr_pos = (target['lat'], target['lon'])

    total_time = (total_dist / speed * multiplier) if total_dist > 0 else 0

    return jsonify({
        "path": full_path,
        "dist": total_dist,
        "time": total_time,
        "sequence": visit_sequence,
        "traffic_multiplier": multiplier
    })

if __name__ == '__main__':
    # 关键修改：禁用 reloader 避免进程重启，提高启动脚本的稳定性
    app.run(debug=True, port=5000, use_reloader=False)