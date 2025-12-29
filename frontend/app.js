$(document).ready(function() {
    const API = 'http://127.0.0.1:5000';
    const map = L.map('map').setView([31.3166, 121.3895], 16);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OSM' }).addTo(map);

    // 图层管理
    const lyrs = {
        base: L.layerGroup().addTo(map),  // 隐形点击层
        hl: L.layerGroup().addTo(map),    // 高亮层 (轮廓/圆圈)
        mk: L.layerGroup().addTo(map),    // 标记层 (图钉/Marker)
        route: L.layerGroup().addTo(map)  // 路线层
    };

    // 状态
    let mode = 'standard';
    let currentMode = 'walk'; 
    let data = {
        all: [],
        s_start: null, s_end: null, 
        t_start: null, t_stops: []  
    };

    // 初始化 Select2
    const selConf = { width: '100%', placeholder: "搜索地点...", allowClear: true };
    $('.poi-select').select2(selConf);

    // 加载数据
    fetch(`${API}/api/locations`)
        .then(r=>r.json()).then(pois => {
            data.all = pois;
            const opts = pois.map(p => new Option(p.name, p.name, false, false));
            $('#sel-start').append([...opts.map(o=>o.cloneNode(true))]);
            $('#sel-end').append([...opts.map(o=>o.cloneNode(true))]);
            $('#sel-tour-start').append([...opts.map(o=>o.cloneNode(true))]);
            $('#sel-tour-add').append([...opts.map(o=>o.cloneNode(true))]);
            
            pois.forEach(p => createClickArea(p));
        });

    function createClickArea(p) {
        let l;
        if(p.polygon && p.polygon.length) l = L.polygon(p.polygon, {color:'transparent', fillOpacity:0});
        else l = L.circle([p.lat, p.lon], {radius:20, color:'transparent'});
        l.on('click', (e) => showPopup(p, e.latlng));
        l.addTo(lyrs.base);
    }
    
    function showPopup(p, latlng) {
        let btns;
        if(mode === 'standard') {
            btns = `
                <button onclick="setPt('s_start', '${p.name}')" class="popup-btn-start">设为起点</button>
                <button onclick="setPt('s_end', '${p.name}')" class="popup-btn-end">设为终点</button>
            `;
        } else { 
            btns = `
                <button onclick="setPt('t_start', '${p.name}')" class="popup-btn-start">设为起点</button>
                <button onclick="addTourStop('${p.name}')" class="popup-btn-add">加入途经</button>
            `;
        }
        L.popup().setLatLng(latlng).setContent(`<b>${p.name}</b><br>${btns}`).openOn(map);
    }

    window.setPt = (key, name) => {
        map.closePopup();
        if(key==='s_start') $('#sel-start').val(name).trigger('change');
        if(key==='s_end') $('#sel-end').val(name).trigger('change');
        if(key==='t_start') $('#sel-tour-start').val(name).trigger('change');
    };
    window.addTourStop = (name) => {
        map.closePopup();
        const p = data.all.find(x=>x.name===name);
        if(p && !data.t_stops.find(x=>x.name===name)) {
            data.t_stops.push(p);
            renderTourList();
        }
    };

    // --- 事件监听 ---
    $('#sel-start').on('change', function() { handleSelectChange('s_start', this.value); });
    $('#sel-end').on('change', function() { handleSelectChange('s_end', this.value); });
    $('#sel-tour-start').on('change', function() { handleSelectChange('t_start', this.value); });
    
    $('#sel-tour-add').on('select2:select', function(e) {
        window.addTourStop(e.params.data.id);
        $(this).val(null).trigger('change');
    });

    function handleSelectChange(key, value) {
        if (!value) {
            updateState(key, null);
            return;
        }

        if (value === 'CURRENT_LOCATION') {
            if (!navigator.geolocation) {
                alert("浏览器不支持定位");
                return;
            }
            if (key === 's_start' || key === 's_end') $('#res-standard').text("正在定位...");

            navigator.geolocation.getCurrentPosition(pos => {
                const gpsNode = {
                    name: "我的位置",
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude,
                    isGps: true,
                    polygon: []
                };
                updateState(key, gpsNode);
            }, err => {
                alert("定位失败: " + err.message);
                $('#res-standard').text("定位失败");
            }, {enableHighAccuracy: true});
        } else {
            const p = data.all.find(x => x.name === value);
            updateState(key, p || null);
        }
    }

    function updateState(key, node) {
        data[key] = node;
        redraw(); 
        if(mode === 'standard' && data.s_start && data.s_end) checkPathStandard();
    }

    function redraw() {
        lyrs.hl.clearLayers(); 
        lyrs.mk.clearLayers();
        
        const draw = (p, c) => {
            if(!p) return;
            // 绘制轮廓 (高亮层)
            if(p.polygon && p.polygon.length) {
                L.polygon(p.polygon, {color:c, fillColor:c, fillOpacity:0.4}).addTo(lyrs.hl);
            } else {
                L.circleMarker([p.lat, p.lon], {radius:10, color:c, fillColor:c, fillOpacity:0.6}).addTo(lyrs.hl);
            }
            // 绘制图钉 (标记层) - 后续算路成功后会被清除
            L.marker([p.lat, p.lon], {opacity: 0.9}).bindPopup(p.name).addTo(lyrs.mk);
        };

        if(mode === 'standard') {
            draw(data.s_start, 'green'); 
            draw(data.s_end, 'red');
        } else {
            draw(data.t_start, 'green');
            data.t_stops.forEach((s) => draw(s, 'orange'));
        }
    }

    function renderTourList() {
        const ul = $('#tour-list').empty();
        data.t_stops.forEach((s,i) => {
            ul.append(`<li><span>${i+1}. ${s.name}</span> <a href="#" onclick="delStop(${i})" style="color:red">x</a></li>`);
        });
        redraw();
    }
    window.delStop = (i) => { data.t_stops.splice(i,1); renderTourList(); };

    function getTime() {
        if($('input[name=time-mode]:checked').val() === 'auto') {
            const d = new Date();
            return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
        }
        return $('#time-input').val() || '08:00'; 
    }

    function calculateArrivalTime(startTimeStr, durationSeconds) {
        const [startH, startM] = startTimeStr.split(':').map(Number);
        const durationMin = Math.ceil(durationSeconds / 60);
        
        let totalM = startM + durationMin;
        let addedH = Math.floor(totalM / 60);
        let finalM = totalM % 60;
        let finalH = (startH + addedH) % 24; 
        
        return `${String(finalH).padStart(2,'0')}:${String(finalM).padStart(2,'0')}`;
    }

    // --- 标准导航逻辑 ---
    function checkPathStandard() {
        if (!data.s_start || !data.s_end) { 
             $('#res-standard').text("请选择起点和终点");
             lyrs.route.clearLayers();
             return; 
        }

        const t = getTime();
        lyrs.route.clearLayers();
        $('#res-standard').html("计算中...");
        
        const url = `${API}/api/find_path?start_lat=${data.s_start.lat}&start_lon=${data.s_start.lon}&end_lat=${data.s_end.lat}&end_lon=${data.s_end.lon}&time=${t}`;
        
        fetch(url).then(r=>r.json()).then(res => {
            if(res.error) { $('#res-standard').text("无路可达"); return; }
            
            // --- 关键修复：只清除图钉，保留轮廓 ---
            lyrs.mk.clearLayers(); 
            // ---------------------------------

            const pathData = res[currentMode].path;
            const dist = res[currentMode].dist;
            const timeSec = res[currentMode].time;
            const col = currentMode === 'walk' ? 'blue' : 'red';
            
            if (pathData && pathData.length > 0) {
                const poly = L.polyline(pathData, {color:col, weight:6}).addTo(lyrs.route);
                map.fitBounds(poly.getBounds().pad(0.2));
            }

            // --- 精度优化：保留1位小数 ---
            const walkMin = (res.walk.time / 60).toFixed(1);
            const bikeMin = (res.bike.time / 60).toFixed(1);
            const currentMin = (timeSec / 60).toFixed(1);

            const trafficTag = res.traffic_multiplier > 1.0 ? `<span class="warn-tag">拥堵 x${res.traffic_multiplier.toFixed(1)}</span>` : '';
            const arriveTime = calculateArrivalTime(t, timeSec);

            let html = `<b>当前模式: ${currentMode==='walk'?'步行':'骑行'}</b> (出发 ${t})<br>`;
            html += `路程: ${(dist/1000).toFixed(2)} km<br>`;
            html += `预计耗时: ${currentMin} 分钟 ${currentMode==='bike' ? trafficTag : ''}<br>`;
            html += `<b style="color:#28a745">预计到达: ${arriveTime}</b><br>`; 
            html += `<hr style="margin:5px 0; border:0; border-top:1px solid #ddd;">`;
            html += `参考: 🚶 ${walkMin}分 | 🚴 ${bikeMin}分`;
            
            $('#res-standard').html(html);
        });
    }

    $('.mode-btn').click(function() {
        $('.mode-btn').removeClass('active');
        $(this).addClass('active');
        currentMode = $(this).data('mode');
        if(data.s_start && data.s_end) checkPathStandard(); 
    });

    // 漫游模式逻辑
    $('#btn-tour-go').click(() => {
        if(!data.t_start || !data.t_stops.length) return alert("请完善漫游点");
        
        const m = $('#tour-mode').val();
        const t = getTime();
        const stopsStr = data.t_stops.map(s => `${s.lat},${s.lon}`).join('|');
        const namesStr = data.t_stops.map(s => s.name).join('|'); 
        
        lyrs.route.clearLayers();
        $('#res-tour').text("规划中...");
        
        const url = `${API}/api/find_tour?start_lat=${data.t_start.lat}&start_lon=${data.t_start.lon}&stops=${stopsStr}&names=${namesStr}&mode=${m}&time=${t}`;
        
        fetch(url).then(r=>r.json()).then(res => {
            const col = m==='walk'?'blue':'red';
            const poly = L.polyline(res.path, {color:col, weight:6}).addTo(lyrs.route);
            map.fitBounds(poly.getBounds().pad(0.2));
            
            let seqHTML = `<b>最优路径顺序:</b><ol>`;
            res.sequence.forEach((name, index) => { seqHTML += `<li>${name}</li>`; });
            seqHTML += `</ol>`;

            // --- 精度优化 ---
            const mins = (res.time / 60).toFixed(1);
            
            const arriveTime = calculateArrivalTime(t, res.time);
            const trafficInfo = res.traffic_multiplier > 1 ? `(含拥堵 x${res.traffic_multiplier.toFixed(1)})` : '';
            
            $('#res-tour').html(`
                ${seqHTML}
                <b>总耗时:</b> ${mins} 分钟 ${m==='bike' ? trafficInfo : ''}<br>
                <b>预计完成:</b> ${arriveTime}<br>
                <b>总路程:</b> ${(res.dist/1000).toFixed(2)} km
            `);
        });
    });

    // 保留了底部代码的清理逻辑，去除了之前手动添加的 search box 交互
    $('.tab-btn').click(function() {
        $('.tab-btn').removeClass('active'); $(this).addClass('active');
        mode = $(this).data('mode');
        $('#panel-standard').toggle(mode==='standard');
        $('#panel-tour').toggle(mode==='tour');
        
        lyrs.route.clearLayers();
        $('#res-standard').text("请选择起点和终点");
        $('#res-tour').html("");
        redraw(); 
    });

    $('input[name=time-mode]').change(function() {
        $('#time-input').prop('disabled', this.value==='auto');
        if(mode==='standard' && data.s_start && data.s_end) checkPathStandard();
    });
    
    $('#btn-reset-view').click(() => map.setView([31.3166, 121.3895], 16));
    $('#btn-clear-all').click(() => location.reload()); 
});